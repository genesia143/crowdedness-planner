"""Development-only cross-route reference sensitivity; not an occupancy model."""
import argparse
from collections import defaultdict, Counter
import json
from pathlib import Path
import sqlite3
from statistics import median


def evaluate(database):
    with sqlite3.connect('file:' + str(Path(database).resolve()) + '?mode=ro', uri=True) as db:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
        if meta.get('training_start') != '2026-10-01' or meta.get('training_end') != '2026-10-21':
            raise ValueError('Expected October 1–21 training model only')
        cells = list(db.execute('''SELECT s.route,s.origin,s.destination,s.hour,
                    s.sampled_passengers*1.0/t.scheduled_crossings
               FROM service_signals s JOIN scheduled_totals t
               USING(route,origin,destination,day_type,hour)
               WHERE s.day_type='weekday' AND s.matched_days>=3
                 AND s.sampled_passengers>=10 AND t.scheduled_days>=4
                 AND t.scheduled_crossings>0'''))
    peak = defaultdict(list)
    for route, start, end, hour, rate in cells:
        if 7 <= hour < 10:
            peak[route].append((hour, rate))
    eligible = [(median([r for _,r in values]), route, len(values))
                for route, values in peak.items()
                if len(values) >= 20 and len({h for h,_ in values}) >= 3]
    eligible.sort(reverse=True)
    if len(eligible) < 6:
        raise ValueError('Need six eligible reference routes')
    refs = []
    for sample in (eligible[:3], eligible[3:6]):
        refs.append({'routes':[{'route':r,'median_peak_rate':v,'cells':n} for v,r,n in sample],
                     'reference':median([v for v,_,_ in sample])})
    def label(rate, ref):
        return 'higher' if rate > 1.25*ref else 'lower' if rate < .75*ref else 'middle'
    counts=Counter()
    for *_, rate in cells:
        a,b=(label(rate,r['reference']) for r in refs)
        counts['cells'] += 1
        counts['changed_label'] += a != b
        counts['changed_high'] += (a == 'higher') != (b == 'higher')
        counts['reference_a_'+a] += 1
        counts['reference_b_'+b] += 1
    return {'training_start':meta['training_start'],'training_end':meta['training_end'],
            'population':'weekday supported route-segment-hour cells; each cell equal weight',
            'reference_method':'median of route median weekday 07:00–09:59 sampled-passengers / scheduled crossings; >=20 supported peak cells and all three hours per route; two disjoint sets of three highest routes',
            'thresholds':'illustrative: lower <0.75 reference, higher >1.25 reference; no physical interpretation',
            'eligible_routes':len(eligible),'references':refs,'comparison':dict(counts),
            'limitations':'Training-only descriptive sensitivity, not validation. Many correlated adjacent segment cells; sample varies by route, matching and service. Scheduled buses, not actual. Peak selection favors high values and does not establish physical crowding or representativeness. Labels and threshold illustrative; do not use for comfort ranking.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args(); result=evaluate(a.database)
    with open(a.output,'x') as f: json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
