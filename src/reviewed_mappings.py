"""Validate user-supplied route-specific stop IDs and produce an audit report."""
import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from model import critical_tokens, normalize, route_patterns

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read_xlsx(path):
    with zipfile.ZipFile(path) as book:
        shared = []
        if 'xl/sharedStrings.xml' in book.namelist():
            root = ET.fromstring(book.read('xl/sharedStrings.xml'))
            shared = [''.join(node.itertext()) for node in root.findall('m:si', NS)]
        sheet = ET.fromstring(book.read('xl/worksheets/sheet1.xml'))
        records = []
        for row in sheet.findall('.//m:sheetData/m:row', NS):
            cells = {}
            for cell in row.findall('m:c', NS):
                column = re.sub(r'\d+', '', cell.get('r', ''))
                value = cell.find('m:v', NS)
                text = '' if value is None or value.text is None else value.text
                if cell.get('t') == 's' and text:
                    text = shared[int(text)]
                elif cell.get('t') == 'inlineStr':
                    text = ''.join(cell.find('m:is', NS).itertext())
                cells[column] = text
            records.append(cells)
        if not records:
            raise ValueError('review workbook is empty')
        header = records[0]
        return [{label: row.get(column, '') for column, label in header.items() if label} for row in records[1:]]


def inspect(review, gtfs, confirmed=False):
    names, patterns = route_patterns(gtfs)
    route_ids = {route: {stop for pattern in variants for stop in pattern} for route, variants in patterns.items()}
    audit = []
    for row in read_xlsx(review):
        route = row.get('route', '').strip()
        name = row.get('ticket_stop_name', '').strip()
        role = row.get('used_as', '').strip().lower()
        decision = row.get('decision', '').strip().lower()
        stop_id = (row.get('correct_gtfs_stop_id', '') or row.get('candidate_gtfs_stop_ids', '')).strip()
        reasons = []
        if decision not in ('', 'correct'):
            reasons.append('decision_not_correct')
        if role not in ('boarding', 'destination') or not name:
            reasons.append('invalid_role_or_name')
        if not stop_id or not re.fullmatch(r'\d+', stop_id):
            reasons.append('missing_or_multiple_stop_ids')
        if normalize(route) not in route_ids:
            reasons.append('route_not_found')
        elif stop_id not in route_ids[normalize(route)]:
            reasons.append('stop_not_on_route')
        target = names.get(stop_id, '')
        score = round(100 * SequenceMatcher(None, normalize(name), normalize(target)).ratio(), 1) if target else None
        if score is not None and score < 80:
            reasons.append('low_name_similarity')
        if target and critical_tokens(name) != critical_tokens(target):
            reasons.append('direction_or_block_difference')
        blocking = {'decision_not_correct', 'invalid_role_or_name', 'missing_or_multiple_stop_ids', 'route_not_found', 'stop_not_on_route'}
        blocked = any(reason in blocking for reason in reasons)
        audit.append({'route':route, 'ticket_stop_name':name, 'used_as':role, 'stop_id':stop_id,
                      'gtfs_stop_name':target, 'similarity_score':score, 'decision':decision,
                      'status':'review' if blocked or (reasons and not confirmed) else 'accepted', 'reasons':' | '.join(reasons)})
    # No silent choice when the same key names different stops.
    targets = {}
    for row in audit:
        key = (normalize(row['route']), normalize(row['ticket_stop_name']), row['used_as'])
        if row['stop_id']:
            targets.setdefault(key, set()).add(row['stop_id'])
    for row in audit:
        key = (normalize(row['route']), normalize(row['ticket_stop_name']), row['used_as'])
        if len(targets.get(key, ())) > 1:
            row['status'] = 'review'
            row['reasons'] = ' | '.join(filter(None, [row['reasons'], 'conflicting_stop_ids']))
    return audit


def write_report(audit, output):
    fields = ['route','ticket_stop_name','used_as','stop_id','gtfs_stop_name','similarity_score','decision','status','reasons']
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8-sig', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=fields); w.writeheader(); w.writerows(audit)
    return Counter(row['status'] for row in audit)
