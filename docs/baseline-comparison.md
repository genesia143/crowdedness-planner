# Do stretch labels beat simpler predictors?

A stretch label ("likely busier / typical / likely quieter than this stretch at other hours") is only useful if it says more than a simple rule would. This check scores the model against three simpler predictors on **exactly the same hours**, using the same target and scoring as [label validation](v1-label-validation.md): training on 1–21 October, then comparing with ticket-sample ranks from the 22–24 October development days. The reserved 25–31 October week is not used.

| Predictor | What it assumes |
|---|---|
| **Model** | Each stretch has its own hourly pattern, learned from that stretch's tickets |
| **Route pattern** | Every stretch follows its route's overall hourly pattern |
| **Citywide pattern** | Every stretch follows the citywide mobile-ticket hourly pattern |
| **Always typical** | A chance reference |

## Results

| Day type | Evaluated stretch-hours | Model | Route pattern | Citywide pattern | Always typical |
|---|---:|---:|---:|---:|---:|
| Weekday | 152,958 | **60.6%** | 55.0% | 48.1% | 35.2% |
| Saturday | 22,862 | **56.7%** | 52.3% | 46.3% | 35.2% |

Share of hours labelled at the **opposite end** (quieter when the target says busier, or the reverse), lower is better:

| Day type | Model | Route pattern | Citywide pattern |
|---|---:|---:|---:|
| Weekday | **4.7%** | 7.0% | 10.5% |
| Saturday | **5.8%** | 7.3% | 12.0% |

## What this shows

- **On this development sample, stretch-level labels agree more often.** They agree with later tickets about 12 points more often than the citywide pattern, and about 5 points more often than the route's own pattern, on both weekdays and Saturdays.
- **They also make fewer serious errors.** Opposite-end mistakes are less than half as common as with the citywide pattern.
- **The gain over the route pattern is modest.** Much of the time-of-day signal is shared along a route; the stretch level mainly adds where a route's busy section shifts during the day.

## Limits

- Agreement is with **later mobile-ticket patterns**, not with people counted on buses.
- Stretch-hours share passengers, so they are not independent observations.
- The development window has two weekdays and one Saturday and no Sunday, so Sunday is not covered.
- These figures come from a model built without the reviewed stop workbook (50.0% of tickets matched rather than 54.8%). The model's agreement here matches `scripts/validate_v1_labels.py` exactly on the same inputs; rerun on the reviewed model with:

```sh
python3 scripts/compare_label_baselines.py --database data/setup/model.db \
  --validation data/setup/validation-22-24.json --gtfs data/input/gtfs --output data/setup/baselines-22-24.json
```

The validation records come from `src/cli.py` run on 22–24 October with the same options as training.
