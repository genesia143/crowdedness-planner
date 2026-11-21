# Development comparison of evidence thresholds

The current split-day model requires three days with matched tickets and ten sampled passengers per route, directed segment, day type and hour. An exploratory alternative requires two days and five passengers. Both additionally require four scheduled weekdays or three scheduled Saturdays/Sundays, three supported hours and two distinct training rates. The tests use the October 1–21 training model and the October 22–24 development data; no final-week records are used.

| Criterion | Current (3 days, 10 passengers) | Looser (2 days, 5 passengers) |
| --- | ---: | ---: |
| Matched development passenger-segments in supported cells | 68.05% | 78.59% |
| Weekday three-band agreement | 61.04% (169,389 hours) | 58.43% (253,118 hours) |
| Saturday three-band agreement | 56.38% (27,522 hours) | 53.30% (68,080 hours) |
| Weekday decisive-hour-pair concordance | 79.90% | 78.91% |
| Saturday decisive-hour-pair concordance | 75.96% | 73.77% |

The development reference is the matched-ticket sample divided by scheduled bus crossings, not physical occupancy. The hour groups and pairwise comparisons overlap and are correlated. Thresholds select different cells and different comparison hours, so the agreement differences are descriptive and cannot isolate a causal effect of the threshold change. Passenger-segment coverage is not the fraction of passengers, journeys, or journey options with useful coverage. There is no Sunday in this development period. In addition, the three-band target ranks are computed among the supported hours with development-period service, so a change in supported hours changes the comparison itself.

Lowering thresholds expands the sample-covered cells while the agreement is lower on its larger comparison set; these figures alone do not establish whether the new labels help specific journeys. They do not justify occupancy claims or a Sunday conclusion. The script also reports a strict 4-day/20-passenger sensitivity; because the training period has only three Saturdays and Sundays, that sensitivity cannot label either weekend day type.

Reproduce from the repository root with the existing local data artifacts:

```sh
python3 scripts/compare_coverage_thresholds.py --database data/otp-trial/model-v1-split-days.db --validation data/otp-trial/validation-v1-split-days.json --gtfs data/otp-trial/gtfs-original --output data/otp-trial/coverage-threshold-study.json
```
