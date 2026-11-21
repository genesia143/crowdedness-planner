# OpenTripPlanner feasibility trial

## What was tested

On this Mac, OpenTripPlanner 2.7.0 with a local Java 21 runtime combined five routes from the original Delhi GTFS archive with the BBBike New Delhi OpenStreetMap extract. The original archive was flattened for OTP; the source archive and the edited stop file were not changed. The smaller city extract has a limited boundary (approximately 76.98–77.50 E, 28.44–28.74 N) and does not cover every Delhi/NCR stop. It is a test input, not a citywide production map.

A cross-city query on 22 October at 08:00 returned a 307DOWN-to-473UP itinerary with a mapped walk of about 3 m between GTFS stops 7674 and 830. A separate walking-only query between Badarpur stop coordinates 2640 and 9702 returned about 811 m on the mapped network. These are OSM-derived estimates, not verified walking paths. A 307DOWN direct journey was also returned. The five-route subset cannot establish complete network routing or the best journey across all routes.

`src/otp_adapter.py` filters walking legs between bus legs against a user-specified maximum and can annotate exact GTFS trip segments with the V1 sample signal. This is a post-filter on returned itineraries: OTP may omit alternatives during its search, so it does not guarantee the best or any valid journey under the limit. Tests cover 1000 m, 1001 m and unknown distances using synthetic legs; the real example passed a 1 km threshold, but a real over-1-km transfer and the planner's search configuration are not yet validated. Walking paths can be missing or unsafe in OSM; no accessibility guarantee is made.

One returned transfer itinerary contained 9 segments on 307DOWN and 30 on 473UP. V1 data was available for 7 and 30 respectively. This checks integration, not crowding accuracy. The V1 model groups tickets by creation/assumed boarding hour, while the trial queries by each segment's scheduled crossing hour; that alignment remains approximate. The API does not yet expose this adapter as an integrated production endpoint.

## Data integrity finding

The edited local `stops.txt` has 35 IDs changed to scientific notation relative to the original ZIP and contains three duplicate rows by ID. The prior reviewed training build used the edited file. With the original feed, V1 matched 916,872 of 1,672,406 training tickets and the review audit accepted 241 of 250 rows. Rebuild model and validation artifacts against the same clean GTFS version before comparing earlier figures. The local matcher now rejects duplicate stop IDs. Save spreadsheet edits in a separate file, preserving IDs as text.

## Runtime and limits

A full northern-zone OSM extract plus the full GTFS feed exhausted a 5 GB Java heap. Even the five-route subset with that regional map ran out of heap while indexing. The 36 MB New Delhi extract plus five routes built successfully; the saved graph was about 60 MB. Scaling to the complete feed and geographic area, checking permissions/attribution for OSM data, deterministic setup for judges, verifying route coverage, and testing a 1 km hard constraint remain open. V1 source data and models are not in Git.
