# Delhi crowdedness-aware journey planner

This project is being developed for Problem 2. It provides a local journey-planner UI and backend that estimates a **relative ticket-derived demand signal** for bus segments.

The October ticket data appears to be a thin and potentially biased sample. Its counts do not establish how many people are aboard, whether a seat is available, or actual crowding. The proposed signal and its evaluation are explained in [the backend design](docs/backend-design.md).

## Current status

A ticket-sample baseline and local API provide direct journeys and experimental mapped journeys through OpenTripPlanner, with walking and segment signals. The UI displays journey alternatives, a configurable extra-arrival-time limit and available ticket-pattern evidence. A same-route, same-stretch provisional comparison is available when every segment has strict evidence; calibrated cross-route comfort, complete routing validation and an independent clean-machine setup check remain open; see [the trial note](docs/otp-trial.md).

## Brief and working assumptions

The PS2 brief asks for a rerunnable ticket-to-crowding pipeline, segment-level outputs, a journey planner or demo showing crowding alongside travel time, a technical note, and checks against familiar patterns and across weeks. It emphasizes a sound crowding model over a polished planner. The brief says the final ticket schema is to be confirmed.

Our working assumptions are that the supplied GTFS schedule approximates service, ticket creation time approximates boarding time, and the matched ticket sample can indicate relative passenger pressure. Each may be wrong or vary by route and time. Missing riders, uneven ticket-channel use and incomplete matching prevent us from inferring actual onboard counts, seat availability or calibrated occupancy from these data alone. Scheduled service is not a count of buses that actually ran. We report evidence and keep low-evidence results unavailable rather than imply an empty bus. October 25–31 is reserved for testing and must not be used for model development; it has already been evaluated for an earlier candidate and is not a fresh independent test for revised models. Agreement with ticket patterns does not establish accuracy against actual passenger counts.

## Run the initial baseline

Requires Python 3.9 or newer and local copies of the ticket CSV and static GTFS directory. From the project directory:

```sh
python3 -m unittest discover -s tests -v
python3 src/cli.py --tickets /path/to/October-Delhi.csv --gtfs /path/to/gtfs --start 2026-10-01 --end 2026-10-21 --output data/training.json
```

The output contains daily sample passenger-journey counts per segment and ticket boarding hour, plus matching counts. Exact normalized stop names must match on a route and produce one unambiguous segment sequence. The output is **not** onboard load, a prediction for an individual bus, or a normalized crowding level. The prototype API, tuning diagnostics and a basic UI exist; final validation and submission hardening remain. Avoid using October 25–31 for model development; see the design note for the proposed split.

### Experimental fuzzy matching

Add `--fuzzy` to try route-conditioned fuzzy stop matching. The matcher requires a similarity score of at least 0.90 and a margin of at least 0.08 over the next candidate; these are provisional rules, not validated accuracy guarantees. Exact matches take priority, and ambiguous stop sequences remain excluded. The output separates exact and fuzzy matches from rejected records. Leave fuzzy matching off for the default baseline until a manually reviewed sample shows it is sufficiently accurate.

## Run the prototype API

After generating the training JSON above, index it and start the server:

```sh
python3 src/index_model.py --input data/training.json --output data/model.db --gtfs /path/to/gtfs
python3 src/api.py --database data/model.db --gtfs /path/to/gtfs --port 8000
```

`GET /health` checks that the server is running. `GET /segments/signal` accepts `route`, `from_stop_id`, `to_stop_id`, and `departure` (an ISO timestamp including an offset). URL-encode parameters. It reports the mean sample count **on days with a matched observation**, and the number of such days. It does not include days without observations in the denominator, and is not a per-bus load, an unconditional forecast, or a calibrated crowding level. A missing signal returns an unavailable status. Stop search and direct scheduled-bus journeys are available when the GTFS directory is supplied. The experimental mapped endpoint supports walking and transfers when a local OTP server is configured; see the trial note. Independent crowding validation and production hardening remain to be completed. The indexer currently loads the full JSON into memory.

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

## Experimental mapped journeys

With a graph built from the same GTFS version, start OpenTripPlanner 2.7 with Java 21, then start the API with `--otp-endpoint http://localhost:18080/otp/gtfs/v1` alongside the `--database` and `--gtfs` arguments above. The graph build, map input, example request, limits and coverage checks are described in [the OTP trial note](docs/otp-trial.md). The mapped endpoint provides scheduled walking, waiting and riding times, plus ticket-derived segment signals where available. The transfer-distance limit filters returned options after the routing search; it does not guarantee that every compliant alternative is found.

The screen at `http://127.0.0.1:8000/` uses the mapped journey endpoint when OTP is configured. It shows provisional per-segment comparisons and missing evidence; it does not show validated occupancy or a cross-route crowding ranking. Representative browser workflows were checked locally; broader routing and accessibility verification remain open.

### Without a running OTP

`/journeys/mapped` answers in this order: the live OTP endpoint if `--otp-endpoint` is given; a recorded response if `--otp-recordings tests/fixtures/otp` is given and the request matches a recorded case; otherwise the built-in planner, when `--gtfs` is supplied. The response's `routing_source` says which answered and `fallback_reason` says why. The built-in fallback searches up to eight stops within 800 m of each end, for direct buses and changes at the same stop only; walking is a straight-line estimate with a 1.3 detour factor at 4.5 km/h, not a street route. Segment signals and the journey evidence summary are attached the same way as for OTP results. The screen shows a "Simplified routing" note when the fallback answered.

```sh
python3 src/api.py --database data/model.db --gtfs /path/to/gtfs --otp-recordings tests/fixtures/otp --port 8000
```

For a contributor-oriented walkthrough of the current setup, see [the setup guide](docs/setup.md). It has not yet been verified on an independent clean machine.

The [submission note](docs/submission-note.md) describes the intended deliverable and its limitations. See the [reproducibility check](docs/reproducibility-check.md), [final ticket evaluation](docs/final-ticket-evaluation.md), and [submission checklist](docs/submission-checklist.md) for the evidence and remaining work. The input ticket data, GTFS feed, reviewed stop workbook and generated model are not distributed in this repository; access to the appropriate data is required to reproduce the demonstrated model.

The experimental model now distinguishes weekdays, Saturdays and Sundays. Rebuild both training records and index after upgrading: older pooled-weekend models are rejected. Saturday and Sunday each have only three training days. Sunday was explored using rotating Sundays and later evaluated against the ticket sample, not actual passenger counts; public holidays are not separately modelled.

## Time and comfort comparison

The mapped API accepts `extra_minutes` (default 20) and optional `latest_arrival` with a timezone offset. It returns the fastest and time-feasible options among those found by the bounded search. In limited cases it may suggest a potentially quieter option on the same route and stretches using strict within-segment ticket patterns. It cannot rank physical comfort across routes or guarantee a seat. See [same-stretch comparison](docs/same-route-alternatives.md) for exact eligibility, caveats and remaining validation.
