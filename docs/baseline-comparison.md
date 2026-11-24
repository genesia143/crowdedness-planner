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
| Weekday | 169,389 | **61.0%** | 55.6% | 48.3% | 35.1% |
| Saturday | 27,522 | **56.4%** | 52.0% | 46.4% | 35.2% |

Share of hours labelled at the **opposite end** (quieter when the target says busier, or the reverse), lower is better:

| Day type | Model | Route pattern | Citywide pattern |
|---|---:|---:|---:|
| Weekday | **4.5%** | 6.7% | 10.4% |
| Saturday | **6.0%** | 7.9% | 12.3% |

## What this shows

- **On this development sample, stretch-level labels agree more often.** They agree with later tickets about 10–13 percentage points more often than the citywide pattern, and about 4–5 points more often than the route's own pattern, on weekdays and Saturdays.
- **They also make fewer serious errors.** Opposite-end mistakes are less than half as common as with the citywide pattern.
- **The gain over the route pattern is modest.** Much of the time-of-day signal is shared along a route; the stretch level mainly adds where a route's busy section shifts during the day.

## Limits

- Agreement is with **later mobile-ticket patterns**, not with people counted on buses.
- Stretch-hours share passengers, so they are not independent observations.
- The development window has two weekdays and one Saturday and no Sunday, so Sunday is not covered.
- These figures were rerun using the reviewed model and reviewed October 22–24 records (241 accepted mappings). They are development-set checks, not a fresh final test; rerun with:

```sh
python3 scripts/compare_label_baselines.py --database data/setup/model.db \
  --validation data/setup/validation-22-24.json --gtfs data/input/gtfs --output data/setup/baselines-22-24.json
```

The validation records come from `src/cli.py` run on 22–24 October with the same options as training.
