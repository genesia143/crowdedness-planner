# Backend design and evaluation decisions

## Goal and limits

Given a route, direction, segment and time, estimate a reproducible historical signal derived from the observed ticket sample. If sufficiently reliable service counts are available, the signal can be normalized by the number of buses. Until independent validation supports a stronger claim, neither form is a measurement of onboard occupancy or seat availability. Compare within a route and segment first; differences in ticket-channel use can distort comparisons across routes and times.

## Candidate workflow

1. Read raw tickets without changing them. Parse `created_at` as an offset-aware time and assign local calendar dates and time slots in Asia/Kolkata. Use `passenger_count`, not ticket rows, as the passenger weight.
2. Match each route code to GTFS route and ordered stop patterns. Match stop names only against candidates on that route, then check that the destination follows the origin. Repeated stops, loops and competing patterns may remain ambiguous. Exclude unresolved records from segment counts and report exclusions by route and time; do not silently choose a match.
3. Add each accepted ticket's passenger count to each traversed segment. This yields observed segment-crossing passenger-journeys, not a bus-trip load. Ticket creation time approximates boarding time; segment crossing time may be later and needs an explicit timing assumption.
4. Aggregate by route, direction or ordered pattern, segment, time slot and day type. Keep daily observations and their coverage, rather than treating tickets as independent days. Start with broad bins and test whether they are stable.
5. If credible observed service counts exist, divide matched sample crossings by corresponding observed bus trips. Otherwise consider scheduled service as a clearly marked approximation only after checking its limitations. Never divide by zero or present an unsupported denominator as observed service.
6. Use earlier dates for training and validation; save the final dates for one evaluation after choices are frozen. Measure errors and ranking performance against the same ticket-derived target, and separately compare to independent onboard observations if available.

## Proposed chronological split

October 1–21: training; October 22–24: validation for selecting matching and model settings; October 25–31: final test. These dates are a starting proposal, not a claim that the data covers each date evenly. Assign by local date, not file row order. Inspect the counts and calendar coverage before accepting the split; do not use test outcomes to tune the model. Freeze the matching rules, denominator, time bins, baseline and metrics before opening the test results. If substantial revisions become necessary, the old test becomes development data and a new independent test is needed.

For an honest prospective test, learn all data-dependent choices—including fuzzy-match dictionaries, normalization and fallback thresholds—from training data alone. Apply the frozen rules to validation and test. GTFS is external reference data, but check its dates and version against October before using schedules as a denominator.

## Candidate API, subject to organizer specification

- `GET /health`: readiness and model version.
- `GET /segments/signal`: route, ordered segment, local departure time; return the signal, reference period, units, sample support, service denominator and source, and an explicit unavailable reason where appropriate.
- `GET /journeys`: origin, destination and departure time; return viable bus options with scheduled journey times and signal for the portion ridden. The initial routing scope and transfer support remain decisions.

The response must distinguish observed counts, normalized scores, comparisons, uncertainty and missing data. Never return a zero for missing evidence. This is a provisional internal contract, not a claim about the organizers' evaluator.

## Evaluation questions to resolve

- What inputs will the evaluator send, and what response schema and units does it expect?
- Are ground-truth outcomes full onboard counts, occupancy categories, ticket counts, or something else? Are they per vehicle trip or aggregated over time and segments?
- What metric determines accuracy, and how are missing predictions handled?
- Will the evaluator supply new tickets, GTFS, dates, or a prebuilt model? Are network access and external data permitted?

A held-out ticket set evaluates generalization to later ticket data. It cannot establish true occupancy or correct selection of a quieter bus if ticket coverage is biased. Independent passenger counts or observations are needed for those claims. Stable sample patterns alone are not proof of crowding accuracy.

## Open decisions

- Confirm evaluator contract, ground truth, metric, and submission constraints.
- Determine team size, deadline and feasibility of independent bus observations.
- Inspect GTFS schedule validity and the available service denominator.
- Decide time bin width, route variant handling, fallback rules and minimum support using training and validation data.
- Decide the smallest journey-planning scope that satisfies the brief and supports a credible demo.
