# Sunday development experiment

This exploratory exercise uses only the already matched October 1–21 training records. It never opens the reserved final-week tickets. For each of October 4, 11 and 18, use the other two Sundays to estimate each route, directed segment and hour, then compare against the excluded Sunday. The GTFS model supplies the same planned service for all three Sundays; this assumption does not establish actual service or occupancy.

An hourly candidate uses the requested hour; a rolling candidate uses the preceding, requested and following hours, without wrapping across midnight. Counts are divided by scheduled crossings for the same window. A candidate requires a minimum number of distinct training Sundays with a sample, minimum sampled passengers, at least three supported hours and at least two distinct rates. Pairwise concordance checks whether the candidate orders two supported hours the same way as the **unsmoothed hourly** target. Zero matched records are treated as zero sampled passengers. Pairs overlap extensively and are not independent.

| Candidate | Target matched passenger-segments covered | Decisive pair concordance |
| --- | ---: | ---: |
| Hourly, 2 days / 5 passengers | 40.2% | 66.6% |
| Hourly, 1 day / 3 passengers | 56.2% | 65.5% |
| 3-hour, 2 days / 5 passengers | 66.1% | 63.9% |
| 3-hour, 1 day / 3 passengers | 78.0% | 63.0% |

These candidates cover different cells, so the figures do **not** establish a controlled accuracy improvement. Passenger-segments are not people or complete journeys; these are relative sample patterns, not observed crowding. They do not cover tickets that could not be matched. A target based on the same ticket pipeline is not independent occupancy ground truth. Three folds from one month provide limited evidence, and wider windows may blur genuine hourly changes.

The recorded Sunday Anand Vihar–Shivaji Stadium case contains 13 journeys, 18 bus legs and 271 segment occurrences. With the experimental 3-hour / 2-day / 5-passenger rule, 119 segment occurrences are supported; 10 legs have at least one supported segment and no legs have every segment supported. Multiple options can repeat the same segment, so these are not independent observations. This is an evidence-coverage test, not proof of correct labels.

Reproduce from the repository root (outputs should be kept outside version control):

```sh
python3 scripts/sunday_window_cv.py --records data/otp-trial/training-v1-split-days.json --database data/otp-trial/model-v1-split-days.db --output /tmp/sunday-window-cv.json
python3 scripts/sunday_fixture_window.py --records data/otp-trial/training-v1-split-days.json --database data/otp-trial/model-v1-split-days.db --fixture tests/fixtures/otp/api/07_av_cp_sun_1800.json
```

Before final evaluation, the evaluator must use the exact chosen production rule rather than its currently hard-coded hourly thresholds. Distinct observed-day counts across a window require daily records or an equivalent index; adding per-hour observed-day counts would double-count dates. Freeze source, model, inputs and evaluation policy together before opening the reserved final week.
