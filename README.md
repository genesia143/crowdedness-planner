# Delhi crowdedness-aware journey planner

This project is being developed for Problem 2. Its first goal is a reproducible backend that estimates a **relative ticket-derived demand signal** for bus segments and helps compare journeys. A UI will follow the API.

The October ticket data appears to be a thin and potentially biased sample. Its counts do not establish how many people are aboard, whether a seat is available, or actual crowding. The proposed signal and its evaluation are explained in [the backend design](docs/backend-design.md).

## Current status

A ticket-sample baseline and a local read-only API with direct and experimental same-stop transfer journeys are implemented. An OpenTripPlanner walking experiment is described in [the trial note](docs/otp-trial.md), but is not integrated into the API. A validated crowding model and UI are not implemented yet. The evaluation interface and ground truth are unspecified in the brief. The October tickets and static GTFS are present elsewhere in the workspace; they are not included in this project.

## Brief and working assumptions

The PS2 brief asks for a rerunnable ticket-to-crowding pipeline, segment-level outputs, a journey planner or demo showing crowding alongside travel time, a technical note, and checks against familiar patterns and across weeks. It emphasizes a sound crowding model over a polished planner. The brief says the final ticket schema is to be confirmed; it does not define an API contract, numerical scoring formula, or hidden-test ground truth. We therefore treat those details as unknown, not established requirements.

Our working assumptions are that the supplied GTFS schedule approximates service, ticket creation time approximates boarding time, and the matched ticket sample can indicate relative passenger pressure. Each may be wrong or vary by route and time. Missing riders, uneven digital-ticket use and incomplete matching prevent us from inferring actual onboard counts, seat availability or calibrated occupancy from these data alone. Scheduled service is not a count of buses that actually ran. We will report coverage and evidence strength, keep low-evidence results unavailable rather than imply an empty bus, and retain the final week as an untouched evaluation set until the approach is fixed. Relative labels must be validated on the tuning period before use; agreement with held-out ticket patterns would not establish accuracy against actual passenger counts.

## Run the initial baseline

Requires Python 3.9 or newer and local copies of the ticket CSV and static GTFS directory. From the project directory:

```sh
python3 -m unittest discover -s tests -v
python3 src/cli.py --tickets /path/to/October-Delhi.csv --gtfs /path/to/gtfs --start 2026-10-01 --end 2026-10-21 --output data/training.json
```

The output contains daily sample passenger-journey counts per segment and ticket boarding hour, plus matching counts. Exact normalized stop names must match on a route and produce one unambiguous segment sequence. The output is **not** onboard load, a prediction for an individual bus, or a normalized crowding level. The full pipeline, API, validation and UI remain to be built. Avoid using October 25–31 for model development; see the design note for the proposed split.

### Experimental fuzzy matching

Add `--fuzzy` to try route-conditioned fuzzy stop matching. The matcher requires a similarity score of at least 0.90 and a margin of at least 0.08 over the next candidate; these are provisional rules, not validated accuracy guarantees. Exact matches take priority, and ambiguous stop sequences remain excluded. The output separates exact and fuzzy matches from rejected records. Leave fuzzy matching off for the default baseline until a manually reviewed sample shows it is sufficiently accurate.

## Run the prototype API

After generating the training JSON above, index it and start the server:

```sh
python3 src/index_model.py --input data/training.json --output data/model.db --gtfs /path/to/gtfs
python3 src/api.py --database data/model.db --gtfs /path/to/gtfs --port 8000
```

`GET /health` checks that the server is running. `GET /segments/signal` accepts `route`, `from_stop_id`, `to_stop_id`, and `departure` (an ISO timestamp including an offset). URL-encode parameters. It reports the mean sample count **on days with a matched observation**, and the number of such days. It does not include days without observations in the denominator, and is not a per-bus load, an unconditional forecast, or a calibrated crowding level. A missing signal returns an unavailable status. Stop search and direct scheduled-bus journeys are available when the GTFS directory is supplied; transfers, walking, independent crowding validation, and production hardening remain to be built. The indexer currently loads the full JSON into memory.

### Scheduled-service denominator

With `--gtfs`, the indexer divides matched ticket-sample passengers by scheduled segment crossings for the same route, segment, calendar date and hour. It includes only days with at least one matched ticket and a scheduled crossing; it reports excluded observed days with no matching scheduled crossing. It honors GTFS calendar exceptions and times after 24:00. Frequency-based GTFS is not supported and is rejected. This is an experimental sample-per-scheduled-crossing proxy: schedules may not reflect actual buses, ticket channel coverage is biased, and ticket boarding hour can differ from the hour of segment crossing. It is not actual occupancy or crowding.

### Experimental segment timing and fuzzy review

The `--segment-timing` flag estimates each segment's crossing time by adding the median scheduled travel time from the ticket's boarding stop across GTFS trips with the same ordered stop path. This is experimental: the ticket creation time may differ from boarding, scheduled travel times may differ from actual travel, and a median across trips can hide time-of-day variation. Records without a suitable timing estimate are reported and excluded. Keep the default boarding-hour baseline until comparisons show whether this improves it.

`scripts/sample_fuzzy.py` creates a reproducible, ticket-row-weighted CSV sample for manual review of accepted fuzzy matches, limited to the supplied dates. The same stop pair can appear more than once because frequent ticket rows receive proportionate weight. Record correctness and reasons in the review columns; do not treat unreviewed output as accuracy evidence. Fuzzy matching remains opt-in.

### Direct journey API (V1 prototype)

With `--gtfs`, `GET /stops?q=...` searches stop names. `GET /journeys?from_stop_id=...&to_stop_id=...&departure=...` returns up to five direct scheduled bus trips departing in the next two hours, sorted by scheduled arrival. The ISO 8601 departure must include a timezone offset. Results include scheduled waiting and ride times and a per-segment sample-per-scheduled-crossing signal when available. URL-encode query parameters, including the `+` in timezone offsets. No transfers, walking, live positions, actual occupancy or crowding ranking are provided. GTFS frequency-based service and missing stop times are not yet supported.

To build V1 with a confirmed review workbook, add `--review /path/to/review.xlsx --confirm-review` to the training command. This uses the workbook's route-valid reviewed mappings, including low-similarity entries confirmed by the reviewer; invalid route/stop combinations remain excluded. The workbook and generated model are excluded from Git, so contributors require appropriate access to those inputs.

### Comparing observed days with all scheduled days

Newly built indexes also return `all_scheduled_days_proxy`: sample passengers divided by all scheduled crossings across the matching training dates, including scheduled days with no matched tickets. This treats those missing observations as zero **in the ticket sample**, which is useful for understanding sparsity but assumes ticket ingestion was complete. It does not establish zero real riders. The original `scheduled_service_proxy` remains available and uses only days with matched tickets; it tends to be higher in sparse samples. Both use scheduled rather than observed service. Rebuild existing indexes to include the new field.

### Experimental one-transfer endpoint

`GET /journeys/transfers?from_stop_id=...&to_stop_id=...&departure=...` returns up to five two-bus itineraries with a transfer at the **same GTFS stop ID**. It assumes a 5–60 minute transfer wait, a first departure within two hours, and arrival within four hours. It does not yet model walking between nearby stops, guaranteed connections, real-time changes, accessibility, or V1 crowding signals on transfer legs. Similar itineraries can appear more than once when buses share several transfer stops. This is an initial experiment, not a full transit router.
