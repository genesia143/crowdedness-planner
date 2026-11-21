# Development-period label agreement

This diagnostic uses the frozen-input V1 training index from 1–21 October and
the matched 22–24 October ticket sample. It compares the API's provisional
within-route, directed-segment and day-type hourly labels with labels produced
by ranking tuning-period sample passengers per scheduled crossing over the
same supported hours with tuning service. Ties use midranks in both periods.
Target groups with fewer than three hours or only one distinct rate are
excluded because their target rank cannot distinguish levels.

| Training day type | Evaluated groups | Evaluated hours | Same label | Agreement |
|---|---:|---:|---:|---:|
| Weekday | 20,564 | 169,389 | 103,390 | 61.0% |
| Weekend (Saturday tuning only) | 7,318 | 54,221 | 29,583 | 54.6% |

Confusion counts below are **training label → tuning label**. Each entry is an
hour within a segment group; many groups share the same tickets and days.

| Day type | Predicted | Target quieter | Target typical | Target busier |
|---|---|---:|---:|---:|
| Weekday | Quieter | 34,728 | 17,664 | 3,283 |
| Weekday | Typical | 16,126 | 29,477 | 12,397 |
| Weekday | Busier | 4,291 | 12,238 | 39,185 |
| Weekend | Quieter | 9,957 | 5,932 | 1,869 |
| Weekend | Typical | 5,647 | 8,494 | 4,577 |
| Weekend | Busier | 2,019 | 4,594 | 11,132 |

Of supported training hours with tuning service, 1,015 weekday and 63 weekend
hours were excluded because the target group had too few hours or no variation.
This is a comparison of ticket-sample ranks, **not occupancy accuracy**. The
target has only two weekdays and one Saturday, is affected by ticket matching,
zero-observation assumptions, scheduled service and timing mismatch, and has
no independent Sunday evidence. Training and target labels use different
numbers of comparison hours if service is missing in tuning. Agreement is
conditional on supported groups; it does not describe coverage of all riders
or journeys. Percentages are descriptive, not confidence intervals. The final
week was not used.

```sh
python3 scripts/validate_v1_labels.py --database data/otp-trial/model-v1-original-gtfs.db \
  --validation data/otp-trial/validation-v1-original.json \
  --gtfs data/otp-trial/gtfs-original --output data/otp-trial/v1-label-validation.json
```
