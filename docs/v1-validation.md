# V1 development validation

**Historical results:** the original figures below use the earlier pooled-weekend model. The currently selected separate-day model and its tuning results are described in [the separate-day analysis](separate-days-analysis.md). Do not mix artifacts between the two models.

The development evaluation is restricted to 22–24 October 2026. Final-week
tickets (25–31 October) remain reserved until the model, matching, labels and
evaluation plan are frozen. Rebuild the tuning records using the *same* clean
GTFS and reviewed mappings as training, with fuzzy matching disabled. Then run:

```sh
python3 scripts/validate_v1.py --database data/otp-trial/model-v1-original-gtfs.db \
  --validation data/otp-trial/validation-v1-original.json \
  --gtfs data/otp-trial/gtfs-original --output data/otp-trial/v1-validation-report.json
```

For each scheduled route segment, hour and date, the target is matched sample
passengers divided by that day's scheduled crossings. The baseline prediction
is the training sample divided by training scheduled crossings for the same
route, segment, hour and day type. The mean absolute error averages the
absolute difference over cells with a training schedule; coverage is reported
separately. Zero matched records count as zero **in the sample**, conditional
on complete ticket ingestion. A schedule-only training cell can have a zero
baseline in this diagnostic even if the API does not provide a usable signal.
The score weights a low-frequency cell the same as a high-frequency cell and
must not be interpreted as an estimate of individual bus occupancy accuracy.

The same stop-matching process creates predictions and targets, so matching
errors or systematic gaps can recur in both. Ticket time is assumed to be
boarding time, yet the current model assigns the entire journey to that hour;
the schedule uses each segment's crossing time. Scheduled service can differ
from actual service. Thursday to Saturday includes no Sunday, so the current
weekday/weekend split cannot be adequately validated here. The report counts
matched segment-hour records with no corresponding scheduled crossing rather
than silently treating them as service-normalised observations.

This diagnostic does not yet measure ranking quality, confidence intervals,
week-to-week stability, commuter-label performance or independent ground-truth
accuracy. It must be rerun after any timing, day-type or matching changes, and
additional metrics should be fixed before the final test is opened.

## First development run

Using the clean original GTFS, confirmed review workbook and training index,
150,127 of 272,465 tickets matched during October 22–24. The diagnostic's
mean absolute difference was 0.186 sample passengers per scheduled crossing
for weekday cells and 0.180 for the Saturday cells grouped as weekend. These
numbers describe a zero-inclusive ticket-sample target, not crowding accuracy;
most cells have zero sample observations. The diagnostic's 100% baseline
coverage includes schedule-only zero predictions and therefore must not be
presented as API evidence coverage. It also found 62,981 matched daily segment
records without corresponding schedule in the same hour. Those timing/service
mismatches and ranking stability require investigation before the labels are
validated. No Sunday is present. The local JSON report stays outside Git.

The schedule-gap diagnostic found that, of the 62,981 observed tuning
segment/day/hour cells without a same-hour scheduled crossing, 50,202 had a
crossing in an immediately adjacent hour (23,392 next only; 12,614 previous
only; 14,196 both), and 12,779 had service elsewhere on the same day. These
are distinct segment-hour cells, not unique tickets or passengers. An adjacent
schedule is consistent with a time-binning mismatch but does not prove its
cause. Diagnostics are restricted to the tuning window.

In an exploratory rebuild using median GTFS offsets to estimate each segment's
crossing hour, the number of observed segment/date/hour cells without a
same-hour crossing fell from 62,981 of 646,955 (9.7%) to 51,108 of 633,059
(8.1%). The grouping changes, so cell counts are not a like-for-like count
of tickets. At passenger-segment weight, the unmatched counts changed from
109,980 of 2,050,630 (5.36%) to 89,252 of 2,050,373 (4.35%); total weights
differ slightly, so this is still an observational comparison. Timing offsets
come from the same static schedule used as denominator and can mechanically
improve alignment without proving actual crossing-time accuracy. No model
selection has been made; train and compare both timing methods on the same
validation targets before making that decision.

## Boarding-time versus estimated crossing-time comparison

Both models use the same October 1–21 tickets, reviewed mappings, clean GTFS,
and scheduled-service denominator. Each was evaluated against both October
22–24 target constructions. Mean absolute difference in ticket-sample
passengers per scheduled crossing (lower is better):

| Training model | Tuning target | Weekday | Saturday (weekend group) |
|---|---|---:|---:|
| Ticket creation / boarding hour | Boarding hour | 0.1861 | 0.1801 |
| Estimated segment crossing hour | Boarding hour | 0.1987 | 0.1855 |
| Ticket creation / boarding hour | Estimated crossing hour | 0.2051 | 0.1891 |
| Estimated segment crossing hour | Estimated crossing hour | 0.1912 | 0.1834 |

Each model fits the target built with the same timing convention better. Neither
construction supplies independent actual crossing times, so these results do
not settle which matches reality. The crossing-time target uses the same GTFS
assumptions as its model and service denominator. The score includes
schedule-only zero-sample cells, weights every segment/date/hour cell equally,
and is not actual occupancy accuracy. The final week remains untouched.

For label availability, 307,747 of 646,955 observed tuning segment/day/hour
records (47.6%) met the provisional training support rules. Weighted by sample
passenger-segments, 1,490,689 of 2,050,630 (72.7%) were labelled. This excludes
unmatched tickets and repeats each passenger over the segments of their trip;
it is not a percentage of unique riders, tickets, or fully covered journeys.
Run `scripts/measure_label_coverage.py` to reproduce it.

A route-level tuning diagnostic shows that these exclusions are uneven. Of
435 routes with at least 1,000 matched tuning passenger-segments, 84 had more
than 10% of that sample without a same-hour scheduled crossing, and 23 had
more than 25%. Passenger-segments repeat each passenger across their ridden
segments and exclude unmatched tickets. This does not prove actual service was
absent or establish the cause, but it warns that the aggregate 5.36% mismatch
can conceal much larger route-specific uncertainty. See
`scripts/route_gap_coverage.py`; no final-week data was used.

The segment API now includes `schedule_alignment` for observed training cells:
matched sample passenger-segments, the number included where a scheduled
crossing was found, the number excluded without one, their fraction, and the
number of affected days. The mapped journey response carries this evidence and
the prototype screen highlights affected segments. This is descriptive
training evidence, not a correction for missing tickets or proof that a bus
failed to run. If no sample observation or service calculation exists, alignment
is unavailable rather than assumed to be zero. No model scores or thresholds
were changed.
