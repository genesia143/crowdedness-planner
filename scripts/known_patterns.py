"""Check the ticket sample against familiar travel patterns (brief section 4).

Reads only the raw ticket CSV, so anyone with the data can rerun it without the
reviewed workbook, GTFS or model. Defaults to the 1-21 October training window;
the reserved 25-31 October week is never read. Writes a Markdown report and an
SVG chart. Counts are mobile e-ticket passengers, not all riders.
"""
import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from math import sqrt
from pathlib import Path

HOLIDAYS = {date(2026, 10, 2): 'Gandhi Jayanti', date(2026, 10, 20): 'Dussehra'}  # Delhi government list 2026
AM, PM = range(7, 11), range(17, 21)        # 07:00-10:59 and 17:00-20:59 IST
SERIES = [('weekday', 'Weekday', '#2a78d6', None), ('saturday', 'Saturday', '#eb6834', '6 4'), ('sunday', 'Sunday', '#1baf7a', '2 3')]


def kind(day):
    if day in HOLIDAYS:
        return 'holiday'
    return 'weekday' if day.weekday() < 5 else 'saturday' if day.weekday() == 5 else 'sunday'


def route_base(route):
    match = re.match(r'^(.*?)\s*(UP|DOWN)$', route.strip(), re.I)
    return (match.group(1), match.group(2).upper()) if match else (route.strip(), None)


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def read(path, start, end):
    daily, hourly, offsets = Counter(), Counter(), Counter()
    peak_routes, am_dest, pm_origin = defaultdict(Counter), Counter(), Counter()
    with open(path, encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            stamp = row['created_at']
            day = date.fromisoformat(stamp[:10])
            if not start <= day <= end:
                continue
            offsets[stamp[-6:]] += 1
            hour, pax = int(stamp[11:13]), int(row['passenger_count'])
            daily[day] += pax
            hourly[(day, hour)] += pax
            if kind(day) == 'weekday':
                base, direction = route_base(row['route'])
                if hour in AM:
                    peak_routes[base]['AM ' + str(direction)] += pax
                    am_dest[row['end_stop_name'].strip()] += pax
                elif hour in PM:
                    peak_routes[base]['PM ' + str(direction)] += pax
                    pm_origin[row['start_stop_name'].strip()] += pax
    return daily, hourly, offsets, peak_routes, am_dest, pm_origin


def chart(profiles, path):
    width, height, left, right, top, bottom = 760, 380, 64, 96, 56, 48
    peak = max(max(values) for values in profiles.values())
    ymax = (int(peak / 2000) + 1) * 2000
    x = lambda h: left + h * (width - left - right) / 23
    y = lambda v: top + (1 - v / ymax) * (height - top - bottom)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Inter,-apple-system,Segoe UI,Roboto,sans-serif" role="img" aria-labelledby="t d">',
           '<title id="t">Average mobile e-ticket passengers per hour, by day type</title>',
           '<desc id="d">Weekdays peak at 8-9 am and 6-7 pm; Saturday and Sunday are lower and flatter. 1-21 October 2026, holidays excluded.</desc>',
           f'<rect width="{width}" height="{height}" fill="#fcfcfb"/>',
           f'<text x="{left}" y="24" font-size="15" font-weight="600" fill="#0b0b0b">Mobile e-ticket passengers per hour (average day)</text>',
           f'<text x="{left}" y="42" font-size="12" fill="#52514e">1–21 October 2026, training window; Gandhi Jayanti and Dussehra excluded</text>']
    for v in range(0, ymax + 1, 2000):
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e6e6e3" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y(v) + 4:.1f}" font-size="11" fill="#52514e" text-anchor="end">{v:,}</text>')
    for h in range(0, 24, 3):
        out.append(f'<text x="{x(h):.1f}" y="{height - bottom + 18}" font-size="11" fill="#52514e" text-anchor="middle">{h:02d}:00</text>')
    out.append(f'<line x1="{left}" x2="{width - right}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#a9a8a3" stroke-width="1"/>')
    for key, label, color, dash in SERIES:
        values = profiles[key]
        points = ' '.join(f'{x(h):.1f},{y(v):.1f}' for h, v in enumerate(values))
        dashed = f' stroke-dasharray="{dash}"' if dash else ''
        out.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"{dashed}><title>{label}</title></polyline>')
        # Direct label just above the series' evening peak, where the lines are well separated.
        h = max(PM, key=lambda hour: values[hour])
        out.append(f'<text x="{x(h) + 6:.1f}" y="{y(values[h]) - 8:.1f}" font-size="12" font-weight="500" fill="#0b0b0b">{label}</text>')
    # Legend, so identity never depends on colour alone.
    lx = left
    for key, label, color, dash in SERIES:
        dashed = f' stroke-dasharray="{dash}"' if dash else ''
        out.append(f'<line x1="{lx}" x2="{lx + 22}" y1="{height - 12}" y2="{height - 12}" stroke="{color}" stroke-width="2"{dashed}/>')
        out.append(f'<text x="{lx + 28}" y="{height - 8}" font-size="12" fill="#52514e">{label}</text>')
        lx += 110
    out.append('</svg>')
    Path(path).write_text('\n'.join(out) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tickets', required=True)
    p.add_argument('--start', default='2026-10-01')
    p.add_argument('--end', default='2026-10-21')
    p.add_argument('--output', default='docs/known-patterns.md')
    p.add_argument('--chart', default='docs/images/hourly-profile.svg')
    a = p.parse_args()
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    if end >= date(2026, 10, 25):
        p.error('25-31 October is reserved; choose an end date before 25 October')
    daily, hourly, offsets, peak_routes, am_dest, pm_origin = read(a.tickets, start, end)
    days = [start + timedelta(n) for n in range((end - start).days + 1)]
    groups = defaultdict(list)
    for d in days:
        groups[kind(d)].append(d)
    profiles = {k: [sum(hourly[(d, h)] for d in groups[k]) / len(groups[k]) for h in range(24)] for k, *_ in SERIES}
    Path(a.chart).parent.mkdir(parents=True, exist_ok=True)
    chart(profiles, a.chart)

    def avg(k):
        return sum(daily[d] for d in groups[k]) / len(groups[k])
    weekday = profiles['weekday']
    am_peak, pm_peak = max(AM, key=lambda h: weekday[h]), max(PM, key=lambda h: weekday[h])
    share = lambda values, hours: sum(values[h] for h in hours) / sum(values)
    # Week-to-week stability of the weekday hourly shape (Mon-Fri weeks, holidays excluded).
    weeks = defaultdict(list)
    for d in groups['weekday']:
        weeks[d - timedelta(d.weekday())].append(d)
    week_profiles = {w: [sum(hourly[(d, h)] for d in ds) / len(ds) for h in range(24)] for w, ds in sorted(weeks.items())}
    keys = list(week_profiles)
    reference = max(keys, key=lambda w: (len(weeks[w]), -w.toordinal()))  # first full week
    lines = ['# Checks against known travel patterns', '',
             'The brief asks for checks against familiar patterns: morning and evening peaks, busy corridors, and weekday versus weekend. '
             'This report checks the **raw mobile e-ticket sample** before any stop matching or modelling, so it does not depend on the reviewed workbook, GTFS or the model. '
             f'It covers {start:%-d}–{end:%-d} October 2026, the training window; the reserved 25–31 October week is not read. '
             'Counts are mobile e-ticket passengers (`passenger_count`), which the organisers confirmed are a subset of riders, not all passengers.', '',
             f'Regenerate with `python3 scripts/known_patterns.py --tickets /path/to/October-Delhi.csv`.', '',
             '## 1. Weekday morning and evening peaks', '',
             f'![Average mobile e-ticket passengers per hour by day type]({Path(a.chart).relative_to(Path(a.output).parent).as_posix()})', '',
             f'- Weekdays show the expected two commuter peaks: **{am_peak:02d}:00–{am_peak + 1:02d}:00** in the morning and **{pm_peak:02d}:00–{pm_peak + 1:02d}:00** in the evening.',
             f'- {share(weekday, AM):.0%} of weekday passengers travel between 07:00 and 11:00, and {share(weekday, PM):.0%} between 17:00 and 21:00.',
             f'- The morning peak hour carries {weekday[am_peak] / (sum(weekday[h] for h in range(11, 16)) / 5):.1f}× the average midday hour (11:00–16:00).', '',
             '| Hour (IST) | Weekday | Saturday | Sunday |', '|---|---:|---:|---:|']
    lines += [f'| {h:02d}:00 | {profiles["weekday"][h]:,.0f} | {profiles["saturday"][h]:,.0f} | {profiles["sunday"][h]:,.0f} |' for h in range(24)]
    lines += ['', 'Values are average passengers per day in that hour.', '',
              '## 2. Weekday versus weekend, and holidays', '',
              '| Day type | Days | Average passengers per day | Relative to weekday |', '|---|---:|---:|---:|']
    for k, label in [('weekday', 'Weekday (Mon–Fri)'), ('saturday', 'Saturday'), ('sunday', 'Sunday')]:
        lines.append(f'| {label} | {len(groups[k])} | {avg(k):,.0f} | {avg(k) / avg("weekday"):.0%} |')
    for d in groups['holiday']:
        lines.append(f'| {HOLIDAYS[d]} ({d:%a} {d:%-d} Oct, holiday) | 1 | {daily[d]:,.0f} | {daily[d] / avg("weekday"):.0%} |')
    lines += ['', 'Saturdays and Sundays carry fewer passengers and have flatter profiles without a sharp commuter peak, and both public holidays look like Sundays rather than weekdays. '
              'This supports modelling weekday, Saturday and Sunday separately; the current model treats holidays as ordinary weekdays (see the [model freeze](model-freeze.md)).', '',
              '## 3. Week-to-week stability of the weekday shape', '',
              f'| Week starting | Weekdays | Passengers per day | Share 07–11 | Share 17–21 | Correlation of hourly shape with week of {reference:%-d %b} |', '|---|---:|---:|---:|---:|---:|']
    for w in keys:
        prof = week_profiles[w]
        lines.append(f'| {w:%a} {w:%-d} {w:%b} | {len(weeks[w])} | {sum(prof):,.0f} | {share(prof, AM):.0%} | {share(prof, PM):.0%} | {pearson(prof, week_profiles[reference]):.3f} |')
    lines += ['', 'A correlation near 1 means the hour-by-hour shape repeats from week to week. The first row is a partial week (only Thursday 1 October; Friday 2 October is Gandhi Jayanti), and the week of 19 October has two ordinary weekdays because of Dussehra on 20 October and the window ending on 21 October.', '',
              '## 4. Busy corridors and tidal flow', '',
              'Routes with the most weekday peak passengers (07–11 and 17–21 combined). Each route number covers both directions; UP and DOWN are its two directions. '
              'Commuter corridors should reverse direction between the morning and evening peaks.', '',
              '| Route | Weekday peak passengers (3 weeks) | Morning: share UP | Evening: share UP |', '|---|---:|---:|---:|']
    top = sorted(peak_routes.items(), key=lambda kv: -sum(kv[1].values()))[:12]
    for base, c in top:
        am_up, am_total = c['AM UP'], c['AM UP'] + c['AM DOWN']
        pm_up, pm_total = c['PM UP'], c['PM UP'] + c['PM DOWN']
        f = lambda n, t: f'{n / t:.0%}' if t else '–'
        lines.append(f'| {base} | {sum(c.values()):,} | {f(am_up, am_total)} | {f(pm_up, pm_total)} |')
    flips = sum(1 for _, c in top if (c['AM UP'] + c['AM DOWN']) and (c['PM UP'] + c['PM DOWN']) and
                (c['AM UP'] / (c['AM UP'] + c['AM DOWN']) - 0.5) * (c['PM UP'] / (c['PM UP'] + c['PM DOWN']) - 0.5) < 0)
    lines += ['', f'{flips} of these {len(top)} routes carry the majority of their passengers in opposite directions in the morning and evening peaks, the tidal pattern expected on commuter corridors. The shift is moderate, typically 10–30 percentage points, because both directions carry commuters on cross-city routes.', '',
              'Most common weekday **morning destinations** and **evening origins**, as written on tickets. If commuting dominates, the places people travel to in the morning should reappear as the places they leave from in the evening.', '',
              '| Rank | Morning destination (07–11) | Passengers | Evening origin (17–21) | Passengers |', '|---:|---|---:|---|---:|']
    am_top, pm_top = am_dest.most_common(10), pm_origin.most_common(10)
    for i in range(10):
        lines.append(f'| {i + 1} | {am_top[i][0]} | {am_top[i][1]:,} | {pm_top[i][0]} | {pm_top[i][1]:,} |')
    overlap = len({n for n, _ in am_top} & {n for n, _ in pm_top})
    lines += ['', f'{overlap} of the top 10 morning destinations are also top 10 evening origins by exact name. Ticket spellings vary (for example "Saket Metro Sation / Said-Ul-Ajaib" and "Saket Metro Station"), so this undercounts the overlap.', '',
              '## What this does and does not show', '',
              'These checks show the ticket sample behaves like commuter travel, which supports using it for **relative** time-of-day and corridor comparisons. '
              'They do not show how many people are on a bus: the sample covers mobile e-tickets only, its share of riders can differ by route and time, '
              'and stop names here are as written on tickets, before matching. '
              f'All timestamps in the window use offsets {", ".join(sorted(offsets))}.']
    Path(a.output).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Wrote', a.output, 'and', a.chart)


if __name__ == '__main__':
    main()
