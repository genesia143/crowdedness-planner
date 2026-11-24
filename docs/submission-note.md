# Problem 2: technical submission note

## The problem and current outcome

The planner returns scheduled bus journey options, including access, transfer and egress walking when the full OpenTripPlanner (OTP) graph is available. It now provides one experimental mobile-ticket pressure indication per eligible option and lets a traveller constrain later arrival relative to the fastest returned option. Cross-route comparisons explicitly assume uniform mobile-ticket uptake; this has not been verified. The resulting indicator is not calibrated physical occupancy, a prediction of seat availability, or a validated comfort ranking.

## Data and method

The main inputs are October ticket records, static GTFS and a reviewed route-stop mapping workbook; these inputs and generated artifacts must be supplied separately. Train on October 1–21; the ticket-processing pipeline maps stops within route and accepted pattern, adds `passenger_count` to each segment traversed, and groups by route, direction, segment, time and day type. Ticket creation time is treated as a boarding-time approximation. Scheduled GTFS segment crossings are used as a proxy for bus service; zero matched ticket samples on a scheduled day enter the all-scheduled-day calculation under the complete-ingestion assumption. The sample is not all riders, and a scheduled bus is not proof it ran.

Strict hourly labels compare a segment with its own supported hours for the same day type. When strict Sunday evidence is missing, the revised local candidate can use a wider three-hour Sunday window with weaker-evidence marking. Neither label is measured occupancy. Lack of sufficient evidence remains unknown. Vehicle capacity, missing pass holders, actual boarding/alighting and ticket-channel selection have not been independently calibrated.

## Journey search and interface

The full graph combines GTFS timetables with OpenStreetMap walking. The API tests departure at the requested time and 10 and 20 minutes later, then applies the maximum extra-arrival window and optional arrival deadline to returned candidates. The router is not exhaustive; the transfer-walk limit is applied after search and may exclude valid alternatives before they are seen. When OTP is unavailable, a limited GTFS fallback estimates walking from straight-line distance and may miss routes or transfers. Route times are scheduled, not GPS-derived. Option labels use fixed exploratory ticket-pressure bands, not physical crowding thresholds; see the [technical reference](technical-reference.md#time-and-comfort-comparison) for the estimator and its unverified assumptions.

## Checks and limitations

The candidate was evaluated against October 25–31 once; this period was not used in its training. Sunday three-band agreement was 42.8% on evaluated supported segment-hours against ticket-sample ranks, not actual occupancy. Weekday and Saturday figures, denominators, correlation and missing-data caveats are in [the final ticket evaluation](final-ticket-evaluation.md). This week is no longer an untouched independent test for a revised model.

A local Python 3.9.6 isolated environment rebuilt the training artifact and index byte-for-byte from the same local data; 102 unit tests passed and a full-router API request and browser workflows were checked. See [reproducibility evidence](reproducibility-check.md) and [journey-search checks](journey-search-validation.md). This is not a clean-machine test: required raw data, reviewed workbook, map extract and Java/OTP graph are supplied separately, and resource use can be substantial.

The busy-route benchmark did not support robust cross-route comparison: different references changed the scale and compressed most cells into one category. See [benchmark sensitivity](benchmark-sensitivity.md). Actual passenger counts, verified vehicle capacities, organizer clarification on sample selection, independent comfort validation, additional routing checks and a fresh independent evaluation dataset remain required. Real-user testing is out of scope by the team's decision.

## Running

Follow [SETUP.md](../SETUP.md) and the [project README](../README.md). Do not train or tune using October 25–31. The project exposes `/health`, `/stops`, `/segments/signal` and `/journeys/mapped`. The UI can use OTP or a limited fallback; both require a compatible GTFS and model index. The optional public Photon place-search service requires internet and can be unavailable; GTFS stop lookup remains available.
