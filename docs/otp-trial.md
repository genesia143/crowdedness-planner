# OpenTripPlanner feasibility trial

## What was tested

On this Mac, OpenTripPlanner 2.7.0 with a local Java 21 runtime combined five routes from the original Delhi GTFS archive with the BBBike New Delhi OpenStreetMap extract. The original archive was flattened for OTP; the source archive and the edited stop file were not changed. The smaller city extract has a limited boundary (approximately 76.98–77.50 E, 28.44–28.74 N) and does not cover every Delhi/NCR stop. It is a test input, not a citywide production map.

A cross-city query on 22 October at 08:00 returned a 307DOWN-to-473UP itinerary with a mapped walk of about 3 m between GTFS stops 7674 and 830. A separate walking-only query between Badarpur stop coordinates 2640 and 9702 returned about 811 m on the mapped network. These are OSM-derived estimates, not verified walking paths. A 307DOWN direct journey was also returned. The five-route subset cannot establish complete network routing or the best journey across all routes.

`src/otp_adapter.py` filters walking legs between bus legs against a user-specified maximum and can annotate exact GTFS trip segments with the V1 sample signal. This is a post-filter on returned itineraries: OTP may omit alternatives during its search, so it does not guarantee the best or any valid journey under the limit. Tests cover 1000 m, 1001 m and unknown distances using synthetic legs; the real example passed a 1 km threshold, but a real over-1-km transfer and the planner's search configuration are not yet validated. Walking paths can be missing or unsafe in OSM; no accessibility guarantee is made.

One returned transfer itinerary contained 9 segments on 307DOWN and 30 on 473UP. V1 data was available for 7 and 30 respectively. This checks integration, not crowding accuracy. The original trial queried by segment crossing hour even though V1 groups tickets by creation/assumed boarding hour. The current adapter reads the indexed model timing convention and uses the bus-leg boarding hour for the boarding-hour model, or the segment crossing hour for the experimental crossing-hour model. Ticket purchase time and actual travel remain uncertain. The mapped endpoint is integrated experimentally and is not production-hardened.

## Data integrity finding

The edited local `stops.txt` has 35 IDs changed to scientific notation relative to the original ZIP and contains three duplicate rows by ID. The prior reviewed training build used the edited file. With the original feed, V1 matched 916,872 of 1,672,406 training tickets and the review audit accepted 241 of 250 rows. Rebuild model and validation artifacts against the same clean GTFS version before comparing earlier figures. The local matcher now rejects duplicate stop IDs. Save spreadsheet edits in a separate file, preserving IDs as text.

## Runtime and limits

A full northern-zone OSM extract plus the full GTFS feed exhausted a 5 GB Java heap. Even the five-route subset with that regional map ran out of heap while indexing. The 36 MB New Delhi extract plus five routes built successfully; the saved graph was about 60 MB. Scaling to the complete feed and geographic area, checking permissions/attribution for OSM data, deterministic setup for judges, verifying route coverage, and testing a 1 km hard constraint remain open. V1 source data and models are not in Git.

## Recreate the trial feed

Use the untouched original GTFS ZIP, rather than a spreadsheet-edited copy. From the repository root, run:

```sh
python3 scripts/prepare_otp_feed.py /path/to/original-gtfs.zip data/otp-trial/trial-gtfs.zip --routes 307DOWN,39UP,8UP,405UP,473UP
```

Create the output directory first. The destination must not already exist. The script selects the routes and their trips, stops, stop times and shapes, validates the referenced stops and shapes, and copies timetable metadata. It writes a flat ZIP that OTP can read. Run the model and OTP on the same source GTFS version; a trial subset is not a full-network feed. This is specific to this feed and trial, not a general-purpose GTFS validator. The archive, output and model are kept outside Git.

The previous experiment used OTP 2.7.0 and Java 21 with a separately obtained BBBike New Delhi OpenStreetMap extract. Install those prerequisites and follow OTP's own graph-building instructions; this script does not download them or establish coverage outside the extract. Place only the intended GTFS ZIP and OSM extract in the OTP graph build directory. A complete setup for judges and full-region graph are still to be validated.

## Backend endpoint

Start the API with the same original GTFS used to build the OTP graph and model, and pass `--otp-endpoint http://localhost:18080/otp/gtfs/v1`. `GET /journeys/mapped` takes `from_lat`, `from_lon`, `to_lat`, `to_lon`, and a timezone-qualified `departure`; `max_transfer_walk` is optional and defaults to 1000 metres. Example:

```sh
curl --get 'http://127.0.0.1:8000/journeys/mapped' \
  --data-urlencode 'from_lat=28.60342055' --data-urlencode 'from_lon=77.30234208' \
  --data-urlencode 'to_lat=28.49313012' --data-urlencode 'to_lon=77.30372712' \
  --data-urlencode 'departure=2026-10-22T08:00:00+05:30' --data-urlencode 'max_transfer_walk=1000'
```

The API filters transfer walks after OTP returns candidates, then attaches V1 segment signals where the OTP trip and stop sequence match the source GTFS. Walking-only itineraries are excluded. The response includes the number of candidates and rejected bus journeys so filtering is visible. This endpoint is experimental: post-filtering can miss valid alternatives, coverage depends on the graph, and scanning stop times per request needs performance work. Arrival and departure walking are not capped by the transfer limit. The current small graph is a feasibility test, not full-city routing.

## Full timetable experiment and timing

A separate graph built successfully with the complete original GTFS feed and the same limited New Delhi OSM extract using a 5 GB Java heap. OTP reported 6,812 stops and 2,554 patterns, but also reported 926 stops not linked for transfers and 915 isolated stops; these counts are different issue categories and may overlap. This demonstrates that the full timetable can fit with the small map, not that all stops or journeys are routable. The earlier failure with the larger map therefore points to map size or its interaction with graph construction as a bottleneck; it does not isolate the exact cause. A full-timetable cross-city request returned 16 bus options in one experiment. Coverage and broader journey tests remain outstanding.

The mapped endpoint returns each leg's scheduled duration and a timing summary for walking, bus riding, and waiting, including the gap from the requested departure. Waiting is calculated from gaps between scheduled leg end and start times. If times are missing or inconsistent, the aggregate is unavailable rather than guessed. These times are scheduled estimates and depend on map quality, walking speed, and service actually running.

## Expanded map coverage experiment

An experimental combined OSM graph was created by clipping the existing northern-zone PBF to 28.15–29.40 latitude and 76.53–77.50 longitude, then merging it with the New Delhi PBF. These are different source extracts and may represent different snapshots; the merge must not be assumed equivalent to a single consistent regional extract. With the original full GTFS, OTP 2.7 built the combined graph with a 6 GB heap. Its report shows 12 isolated stops, down from 150 on the northern extract alone and 915 with the original city-only graph. The 12 are around 28.81–29.10 N, 77.23–77.27 E and need investigation; no unverified straight-line walking paths are fabricated for them. OTP also reported 38 stops with no nearby transfer, which is a separate condition and can be normal. The counts do not prove all walking routes are safe, connected, or correct.

To reproduce the extract, install `osmium==4.3.2` in a Python environment and run:

```sh
python3 scripts/prepare_otp_map.py --regional /path/to/northern-zone.osm.pbf --city /path/to/newdelhi.osm.pbf --output-dir data/otp-trial/combined-rebuild
```

The output directory must not already exist. Put the resulting `combined.osm.pbf`, the flattened original GTFS ZIP, and a `build-config.json` containing `{"dataImportReport":true}` in a separate OTP build directory; then run OTP 2.7 with Java 21 and `--build --save`. Inspect the report and test representative journeys. This is an experiment, not yet a packaged one-command judge setup or a validated complete-coverage graph.

## Single-source India extract

A newer experiment cropped the [Geofabrik India PBF](https://download.geofabrik.de/asia/india.html) to the same bounds using `scripts/prepare_otp_map.py --regional /path/to/india-latest.osm.pbf --output-dir data/otp-trial/india-rebuild`. No `--city` argument is needed. The 1.6 GB source is needed only to prepare the crop, and the crop was about 58 MB. OTP 2.7 successfully built the full GTFS graph from this single-source crop with a 6 GB heap and `dataImportReport` enabled. It reported **zero isolated stops** and 30 stops with no nearby transfer stops. Zero isolated stops means OTP linked all timetable stops to its street graph; it does not prove walking paths are correct, safe, connected to every other point, or sufficient for every requested transfer. Wider sample journey checks, map attribution, input-version pinning and judge setup remain necessary.

A direction-specific check from GTFS stop 9785 (Baraut) to 9792 (Mandola), departing 22 October 2026 at 08:00 IST, returned four bus itineraries on the single-source graph; one reported 20 minutes' wait and about 110 minutes' scheduled bus time. A first check using the opposite-direction stop coordinates returned no options, illustrating the need for direction-aware stop selection and more comprehensive tests.

## Transfer limit investigation

The running OTP 2.7 `planConnection` schema exposes transfer count and slack preferences, but its `TransferPreferencesInput` has no per-request transfer walking-distance field. Graph-build transfer-duration limits are not equivalent to a caller's distance limit: walking speeds and street paths affect the relationship, and changing graph-wide settings cannot implement arbitrary per-request limits. The endpoint therefore continues to filter OTP's returned itineraries by the user's distance, with the documented risk that an otherwise suitable alternative was not returned. Search-window, filter-debug and pagination experiments are needed to measure and reduce that risk; no completeness guarantee is made.

## Alternative filtering probe

`scripts/probe_otp_alternatives.py` compares normal `planConnection` output with OTP's `LIST_ALL` itinerary-filter debug mode for the same coordinates and departure. Debug output is diagnostic and can include results that OTP deliberately excluded; it must not be sent directly to commuters.

With the full GTFS and India-crop graph, on 22 October 2026 at 08:00 IST, the cross-city test from (28.60342055, 77.30234208) to (28.49313012, 77.30372712) returned 16 normal results and 22 debug results. Five additional debug bus candidates passed the current 1 km transfer-distance check; OTP marked one as similar to another itinerary and four as outside the search window. A Baraut-to-Mandola test returned four normal and five debug results; the extra candidate was outside the search window. These are exploratory cases: they confirm OTP filters candidates before the API sees them, not that our distance filter has caused an otherwise suitable itinerary to be lost. The similarity and search-window filters have legitimate purposes, and debug mode does not guarantee every feasible route was generated.
