# V1 development validation

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
