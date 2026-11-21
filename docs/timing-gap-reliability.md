# Timing gap and label agreement: development analysis

This exploratory analysis uses the original pooled-weekend V1 model trained on
October 1–21, and October 22–24 tuning data. It does not use the final week.
For each route, the gap is the fraction of matched training passenger-segments
excluded because no scheduled crossing was recorded in the same hour. The
tuning labels are generated once, then evaluated segment-hours are filtered
by their route's **training** gap. Ranks are not recalculated for each filter.

| Maximum training route gap | Weekday retained | Weekday label agreement | Weekday opposite-end disagreement | Saturday retained | Saturday label agreement | Saturday opposite-end disagreement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No restriction | 169,389 (100%) | 61.04% | 4.47% | 54,221 (100%) | 54.56% | 7.17% |
| 25% | 165,739 (97.85%) | 61.12% | 4.43% | 53,896 (99.40%) | 54.57% | 7.19% |
| 10% | 146,904 (86.73%) | 61.65% | 4.20% | 51,472 (94.93%) | 54.77% | 7.11% |
| 5% | 129,140 (76.24%) | 61.93% | 4.11% | 46,823 (86.36%) | 54.91% | 7.05% |

The 5% filter removes almost a quarter of evaluated weekday segment-hours but
increases agreement by only 0.89 percentage points in this sample; Saturday's
increase is 0.35 points. The filtering comparison changes the selected population,
so it does not demonstrate improved accuracy on any particular rider or route.
The denominator for retained fractions is the original evaluated segment-hour
population, not all journeys. Groups are correlated; tuning has only two
weekdays and one Saturday, and targets share the schedule and matching
assumptions. These figures do not measure actual occupancy or causal impact.

**Decision implication:** evidence does not currently justify suppressing a
large share of labels solely using a route-wide gap threshold. Keep the timing
caution visible; reassess the newly separated Saturday model and alternatives
before freezing. The route-level metric can conceal variation across individual
segments, and reported thresholds were exploratory, not preregistered.

Run with the old pooled artifacts (output must not already exist):

```sh
python3 scripts/timing_gap_reliability.py --database data/otp-trial/model-v1-original-gtfs.db \
  --validation data/otp-trial/validation-v1-original.json --gtfs data/otp-trial/gtfs-original \
  --output data/otp-trial/timing-gap-reliability-pooled.json
```
