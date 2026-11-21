# Rotating-week weekday validation

Using only the already-built October 1–21 development records, train on two of the three seven-day blocks and compare to the third. Each fold uses the existing strict weekday support thresholds (three observed days, ten sample passengers, four scheduled days, three supported hours and two distinct rates). Scheduled service with no matched sample contributes zero sample passengers, assuming complete ingestion. This checks ordering of ticket-sample-per-scheduled-crossing values, not actual occupancy or three-band label accuracy.

| Held-out development week | Decisive hourly-pair concordance | Coverage of matched, scheduled target passenger-segments |
| --- | ---: | ---: |
| 1–7 October | 82.6% | 77.3% |
| 8–14 October | 84.0% | 78.0% |
| 15–21 October | 82.5% | 78.9% |

These are conditional on supported cells and comparable scheduled target hours. Hours and pairs share observations, train sets overlap between folds, and tickets within a journey contribute to multiple stretches; folds are not independent trials and coverage is not journey or population coverage. Holidays remain included. Saturday and Sunday are excluded: the current weekend rule requires observations on all three training weekends, while each fold has only two. Excluded observations without matching scheduled service amount to 519,511 sample passenger-segments across the three development weeks. This is not an independent occupancy check and cannot assess data missed by matching.

Reproduce using the existing training-only artifact:

```sh
python3 scripts/rotating_week_validation.py --records data/otp-trial/training-v1-split-days.json --gtfs data/otp-trial/gtfs-original --output data/otp-trial/rotating-week-development.json
```

The script refuses other declared ranges and out-of-range records; it does not read October 25–31 data. The October final week was already used to test an earlier candidate and is not an untouched test for a revised candidate.
