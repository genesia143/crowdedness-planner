# V1 model freeze proposal and final evaluation plan

**Status: proposal, not frozen. Do not use the final week for model selection.**
The development results support retaining a simple baseline, but the current
labels and their use in journeys still need checks before a freeze is declared.

## Proposed baseline

- Train on 1–21 October 2026 and use 22–24 October for development only.
- Use the original GTFS feed and the same reviewed route-specific stop
  mappings for training and evaluation; keep automatic fuzzy matching off.
- Assign each matched ticket's passenger count to each traversed directed
  segment in its ticket-creation hour, interpreted provisionally as boarding
  hour. Use IST. Actual purchase and boarding times are unverified.
- Use weekday and weekend categories as implemented. Saturday and Sunday are
  pooled; Sunday and holidays lack separate tuning evidence.
- For each route, directed segment, hour and day type, divide matched sample
  passengers on scheduled cells by scheduled crossings across training days.
  A scheduled day with no matched records contributes zero sample passengers,
  conditional on complete ingestion; this is not an empty-bus observation.
- The provisional within-segment hourly label uses at least three matched
  days, ten sample passengers, four scheduled days, three supported hours and
  two distinct rates. Tied values use midrank; below one-third is likely
  quieter, above two-thirds likely busier, and the rest typical. Otherwise
  report insufficient evidence. Comparisons are within the same route,
  directed segment and day type, not between routes or actual occupancy.

This is a defensible starting point, not proof of an optimal threshold or a
validated confidence level. A crossing-hour model and alternative thresholds
have been explored, but neither has independent timing or occupancy ground
truth. See [development validation](v1-validation.md),
[ranking diagnostics](v1-ranking-validation.md), and
[support sensitivity](v1-support-sensitivity.md).

## Before freezing

1. Check how the API summarises multiple segment labels, especially unknown
   segments, and ensure it cannot imply a cross-route occupancy comparison.
2. Measure label outcomes and coverage on the tuning dates, including ties,
   low support, zero observations and cases with no scheduled crossing. The
   existing ranking metric measures pair ordering, not label accuracy.
3. Lock the exact training inputs, reviewed mapping, model options, source
   revision, output artifact and evaluation code, with hashes or equivalent
   identifiers. Save a reproducible command and retain the training metadata.
4. Implement and test a separate final-week evaluator. Existing development
   scripts explicitly reject dates after 24 October; do not weaken that guard
   without an equally explicit final-evaluation boundary. Verify the evaluator
   does not change model parameters, matching rules or training inputs.

## Final-week protocol

The optional `scripts/freeze_manifest.py` can record SHA-256 fingerprints of
named artifacts before evaluation. It does not make the model-selection
decision and does not itself enforce the final-week protocol. For a meaningful
snapshot, include the trained index, clean GTFS, reviewed mappings, relevant
model and matching source, and the final evaluator. Use a stable set of names
for creation and verification. Preserve the training provenance and model
options separately; hash identifiers do not prove how an artifact was built.
Do not point this utility at the October ticket file: creating the snapshot
must not read the reserved records. Verify the snapshot immediately before and
after running the separately guarded evaluator. Do not overwrite a previous
manifest or a previous evaluation report.

After the above choices and evaluator are fixed, evaluate 25–31 October once
as a held-out report. Apply the frozen matching and feature rules. Report the
number of in-period tickets, matched tickets and sample passengers; scheduled
and unscheduled matched segment observations; API label availability with
clear denominators; zero-inclusive sample-rate error and decisive hourly
ranking agreement with ties and group counts. Break out weekday, Saturday and
Sunday results even though the model currently pools the latter two. Explain
that Sunday is an untested subgroup, pairs share observations, and match rate,
scheduled service, timing and ticket uptake can bias findings. Never present
these metrics as ground-truth bus occupancy accuracy.

Record unexpected failures and results without silently changing the model and
reusing this week as a fresh test. Any later model revision needs another
independent evaluation period or an explicit qualification that the week is no
longer an untouched holdout.

## Provenance limitations and target generation

The evaluator accepts an already-built JSON target. A manifest proving the
review workbook and source files did not change does **not** prove that those
files generated that target. Before any final evaluation, record the exact
command, options, model and input snapshot, and independently verify the
expected target-building procedure. With the proposed boarding-hour V1, the
intended command after freeze is:

```sh
python3 src/cli.py --tickets /path/to/October-Delhi.csv --gtfs /path/to/clean-gtfs \
  --review /path/to/confirmed-review.xlsx --confirm-review \
  --start 2026-10-25 --end 2026-10-31 --output /path/to/new-final-target.json
```

Do not add `--fuzzy` or `--segment-timing` for this proposal. The target command
reads the October file and should be run only once the model and evaluation
policy are frozen. Record the target file hash after its creation and the
manifest and output hashes in the evaluation record. These steps improve
auditability but do not independently establish that the data or matching is
correct. Treat the final week as used after inspecting its results; subsequent
changes need new independent test data for an unbiased final assessment.

The prepared evaluator reports label agreement by weekday, Saturday and
Sunday against within-subgroup ticket-sample ranks, and separately reports
matched passenger-segments with and without a same-hour scheduled crossing.
Coverage is reported both among scheduled matched sample passenger-segments
and among all matched sample passenger-segments. It fingerprints the target
before and after evaluation and records that fingerprint in the report. These
checks do not prove that the target was generated with the frozen command, do
not prevent a separate rerun under another filename, and do not validate
occupancy. Review the code and complete the freeze procedure before use.

A proposed local snapshot was created and verified for the current training
index, clean GTFS, reviewed workbook, source directory and evaluation scripts.
It is an audit aid, not a model freeze; later code or input changes invalidate
it and require a new snapshot. It does not include or read the ticket file.
