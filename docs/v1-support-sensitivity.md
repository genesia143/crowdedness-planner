# Tuning-period sensitivity of evidence thresholds

The provisional labels currently require at least three matched days, ten sample passengers, four scheduled days and three supported hours in each route/directed-segment/day-type group. The first two rules are choices, not calibrated confidence levels. We compared them with looser and stricter alternatives using the same October 1–21 training index and October 22–24 tuning observations. No final-week data was used.

| Minimum matched days / passengers | Matched tuning passenger-segments covered | Weekday decisive-pair agreement | Saturday decisive-pair agreement |
|---|---:|---:|---:|
| 2 / 5 | 82.1% | 78.9% | 72.5% |
| 3 / 10 (current) | 72.7% | 79.9% | 74.4% |
| 4 / 20 | 59.6% | 81.5% | 75.6% |

All variants additionally require four scheduled days, at least three supported hours and at least two distinct training rates. Tuning rates use sample passengers divided by scheduled crossings, including scheduled zero-sample days. A comparison is decisive when neither the training nor tuning rates are tied; the report counts ties separately. Ranking is calculated separately for each route and directed segment. Each variant evaluates a different set of hours and pairs: these numbers describe a coverage/reliability tradeoff, not a controlled accuracy improvement on the same examples. Pairs overlap extensively and are not independent. Saturday is evaluated using the weekend training category, which also includes Sunday; no Sunday is present in tuning. Passenger-segments are not unique tickets, people, or complete journeys. Neither the matching-derived sample nor these scores establish actual occupancy. This exploratory tuning cannot serve as a final holdout result.

Reproduce with:

```sh
python3 scripts/sensitivity_support.py --database data/otp-trial/model-v1-original-gtfs.db \
  --validation data/otp-trial/validation-v1-original.json --gtfs data/otp-trial/gtfs-original \
  --output data/otp-trial/support-sensitivity.json
```

The tradeoff does not by itself establish an optimal threshold. Keep the existing rule until the team decides how much additional coverage is worth the lower agreement and assesses label-level performance; freeze the choice before the final-week evaluation.
