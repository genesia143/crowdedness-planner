# Journey crowd-information coverage: 200 searches

The existing planner and model were tested on 200 reproducibly sampled GTFS stop-to-stop searches, using seed `20261124`, dates 2–8 November 2026, 06:00–22:00 IST, a 1 km transfer-walk limit and the default 20-minute extra-arrival limit. The model was built from October 1–21; no October 25–31 ticket records were used in this exercise. All searches used OpenTripPlanner and all three departure offsets (0, 10 and 20 minutes) completed. The study measures availability of the current **relative mobile e-ticket pattern label**, not its accuracy or actual occupancy.

## Results

Among 200 searches, 199 returned at least one eligible option and one returned none. Of those 199 searches, **166 had at least one eligible option with a label on at least one stretch**, while **33 had no label on any eligible option**. These 166 searches can still have other options without labels.

Across the **1,102 eligible journey options** in those searches:

| Coverage | Options | Share |
| --- | ---: | ---: |
| No stretch has a crowd label | 500 | 45.4% |
| Some stretches have labels; others or a bus leg do not | 571 | 51.8% |
| Every stretch has a label | 31 | 2.8% |
| **Total** | **1,102** | **100%** |

Of the recorded stretch occurrences, 11,195 out of 45,520 (24.6%) had labels. This is a segment-occurrence measure: long journeys and repeated route options contribute more observations, so it is not a percentage of passengers or distinct route segments. A further 34 option-level bus-leg occurrences had no segment details, and their unknown number of stretches is not in this denominator.

| Departure day | Searches | Eligible options | Options without any label | Options with at least one label |
| --- | ---: | ---: | ---: | ---: |
| Monday–Friday | 144 | 813 | 319 (39.2%) | 494 (60.8%) |
| Saturday | 28 | 145 | 119 (82.1%) | 26 (17.9%) |
| Sunday | 28 | 144 | 62 (43.1%) | 82 (56.9%) |

The model provides a weaker-evidence three-hour fallback on Sunday, but not on Saturday. Sunday results include 1,429 broader-window labelled stretch occurrences, whereas Saturday has none. This design difference is a plausible contributor to the coverage difference, not proof of its cause; the sample is small and the route and time mix also differs. The three-hour labels do not establish an exact hourly pattern.

Without applying the 20-minute filter, the router returned 5,534 options: 2,699 without any label, 2,671 partial and 164 fully labelled. In 189 of the 199 searches with results, at least one returned option had some information. The normal UI initially shows only three options from the time-eligible set, so these counts do not measure the first screen specifically.

## Sampling and interpretation

Origins and destinations were selected uniformly from GTFS stop rows in the broad bounding box 28.4–28.9 latitude and 76.85–77.4 longitude, with straight-line separation of at least 2 km. Four 4-hour time bands were equally represented; days of the week had 28–32 cases each. Locations are stops, not population-weighted addresses or a sample of actual user demand. The bounding box can include places outside municipal Delhi; long and peripheral stop pairs can be overrepresented. Individual route options are correlated within searches. These figures describe this test, not a representative percentage of real Delhi travellers. The router's search is bounded, and the transfer-walk filter applies after routing, so an unreturned feasible option is not measured here.

The data owner confirmed that the supplied October dataset covers tickets issued through the mobile e-ticketing app. Its share of all riders and how that share differs by route, time and day are unknown. Available labels compare a stretch to that stretch's own hours within the relevant day type; they do not imply seats, absolute occupancy, or a reliable cross-route comfort ranking. Missing labels must not be interpreted as quiet buses.

The strongest next experiment is to test a Saturday broader-window fallback and other evidence-pooling rules on development dates, then report both coverage and correctness against suitable development holdouts. Do not choose rules using the already inspected October 25–31 final-week results. Comparing against an independent source of passenger counts would still be required to validate physical crowding.

## Reproduction and provenance

The runnable sampler is [audit_journey_coverage.py](../scripts/audit_journey_coverage.py); full case-level inputs and option-level summaries are stored locally at `data/otp-trial/journey-coverage-200.json`, which is excluded from Git. The run used commit `3dec8f05cdbfeba0ff664cdcb49fbf7bce1d84d3`, model database SHA-256 `59c0ebec4d6324e357223266cc47e504d3613df6969ff853796c4f31a71dd9bf`, and GTFS stops file SHA-256 `39cfd8f05300a3307a53785605ceba2c3bef8d35cf8ed9265cd22e478d297dde`. OTP's full graph and GTFS are local inputs; the model and original dataset are not committed.
