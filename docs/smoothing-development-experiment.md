# Development experiment: shrinkage and neighbouring stretches

This exploratory comparison uses the October 1–21 model and October 22–24 development ticket records only. The later week was not read. It is not a test of actual bus occupancy or a comparison of commuter label accuracy.

For each route-direction segment-hour with at least one uniquely connected neighbouring segment, compare three fixed predictions of ticket-sample passengers per scheduled crossing:

* Baseline: segment-hour sample passengers divided by scheduled crossings over training days.
* Temporal shrinkage: blend that rate with its three-hour pooled rate, weighted by sample passengers / (sample passengers + 10). This is a heuristic, not a calibrated posterior or confidence probability.
* Spatial smoothing: 75% segment-hour rate and 25% the average of its eligible immediately adjacent segment rates. A shared stop is eligible only when its route connectivity is unambiguous.

The target is development-day matched passengers divided by the average scheduled daily crossings from training, including segment-day-hours with no matched tickets. Zero is a sample observation only, and assumes the ingestion was complete. All three methods are compared on exactly the same cells; a cell is not an independent person or journey.

| Day type | Segment-day-hours | Baseline MAE | Temporal MAE | Spatial MAE |
|---|---:|---:|---:|---:|
| Weekday (two days) | 1,917,414 | 0.18620 | 0.19358 | 0.18660 |
| Saturday (one day) | 958,707 | 0.18243 | 0.18609 | 0.18263 |

For these fixed settings neither method improved mean absolute error. This does not prove all smoothing or shrinkage is ineffective, nor does it assess label coverage or whether model outputs correlate with physical crowding. Most cells have zero sampled tickets; MAE can favour low predictions. This comparison does not assess Sunday and assumes the schedule per day is constant. Missing ingestion, selection bias, boarding-time approximation, correlated segments and noisy one-day target measurements limit interpretation. The parameters were fixed before this run; do not tune repeatedly on the same observations and call the result independent validation.

Reproduce, choosing a new output file:

```sh
python3 scripts/experiment_smoothing.py --database data/otp-trial/model-v1-split-days.db --validation data/otp-trial/validation-v1-split-days.json --output data/otp-trial/smoothing-development.json
```

Do not adopt either heuristic as a production rule based on this test. Future comparisons should include appropriate ranking or band metrics, journeys and uncertainty, across rotating development dates and independent observations where available.
