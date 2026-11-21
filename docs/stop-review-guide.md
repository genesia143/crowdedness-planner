# Reviewing ticket stop names

The review sheet lists ticket stop names that do not match exactly against GTFS stops on the same route. It uses training tickets only and sorts by the number of affected ticket rows; a row count is not necessarily a passenger count. Boarding and destination uses are listed separately. The sheet is a prioritized work list, not a random sample and not an accuracy measurement.

1. Open the CSV in a spreadsheet and leave the original ticket and GTFS files untouched.
2. Check that the ticket name and suggested GTFS stop refer to the same place **on the listed route and direction**. Directions, block letters and separate sides of a road matter. Similar spelling alone is not enough.
3. In `decision`, enter `correct`, `incorrect`, or `unsure`. If you can confidently identify the right GTFS stop ID, add it in `correct_gtfs_stop_id`; otherwise leave that field blank and explain in `notes`. When more than one candidate ID appears, identify the correct one rather than approving all of them. If unsure, leave it unresolved.
4. Save as CSV. Do not change route or ticket spelling columns: they are the lookup keys. We will validate and apply reviewed mappings in a separate step; merely editing the sheet does not yet change the model.

A suggested name may be blank because the matcher was unsure. Its absence does not mean the stop is absent from GTFS. Use the route and GTFS stop locations or trusted local knowledge to resolve it. Frequency-based prioritization improves coverage, but we also need a separate random sample to estimate matching precision.

To regenerate the sheet, use `scripts/prepare_stop_review.py --tickets <ticket.csv> --gtfs <gtfs-directory> --start 2026-10-01 --end 2026-10-21 --output data/stop-review.csv`. Data outputs are excluded from Git. The reserved test dates must not be used to build the review queue.

## Audit and use the reviewed Excel file

Run `python3 scripts/audit_reviewed_stops.py --review <review.xlsx> --gtfs <gtfs-directory> --output data/reviewed-stop-audit.csv`. The first sheet's `correct_gtfs_stop_id` is used when supplied; otherwise a single ID in `candidate_gtfs_stop_ids` is treated as the proposed ID. Only blank or `correct` decisions can be accepted. Each row is checked against the route and given a 0–100 character similarity score based on Python's `SequenceMatcher` after normalization. Scores are not probabilities of correctness.

The audit holds rows for review when the score is under 80, the route or stop is missing, the ID is not on that route, IDs conflict, directions or block labels differ, or the decision is not `correct` or blank. The cutoff is a provisional conservative rule, not a measured accuracy threshold. Low scores can be legitimate aliases. With `--review <review.xlsx>`, the training CLI uses only rows marked accepted by this audit, for the specified route and boarding/destination role. It still requires one unambiguous ordered trip path. The source workbook is not modified. The review sheet and derived audit remain local under `data/`.

If the reviewer explicitly confirms the mappings, `--confirm-review` on both the audit and training CLI accepts spelling-score and directional-word warnings while retaining their reasons in the audit. It still blocks missing or multiple IDs, IDs not on the specified route, conflicting IDs, and explicitly incorrect or unsure decisions. This option should only be used for a workbook the reviewer has confirmed; it does not prove that a physical stop is correct.

## Remaining-coverage diagnosis

`scripts/diagnose_coverage.py` categorizes each valid training-period ticket once: route missing, one or both stop names unresolved, stop path unavailable or ambiguous, or matched. `scripts/rank_unmatched_stops.py` then ranks unresolved route/name/role combinations using the detailed diagnostic. Its highest-spelling-similarity candidate is only a suggestion: it may be a geographically or directionally wrong stop, even when the score is high. Do not import candidates automatically. One ticket can contribute to two ranked stop names, so counts across rows must not be added as unique tickets. The prioritized list is not a random validation sample.
