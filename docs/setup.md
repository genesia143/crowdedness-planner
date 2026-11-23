# Reproducing the backend

This is a working setup guide for contributors; an independent clean-machine run is still needed. Run the commands from the repository root. The ticket CSV, reviewed stop workbook, GTFS, map data, trained model and OpenTripPlanner (OTP) graph are **not** included in Git. Obtain the permitted source files separately. Keep them in `data/` or another ignored location, and do not commit them.

## Inputs and versions

- Python 3.9 or later. The baseline and API use the standard library. Run the unit tests with `python3 -m unittest discover -s tests -v`. Python 3.15 produced a test error in an earlier run; use a version on which the suite passes and record the version alongside your results.
- The original October ticket CSV and original static GTFS archive. Extract the GTFS to a directory and identify the directory containing `stops.txt`, `routes.txt`, `trips.txt` and `stop_times.txt`; use that same directory throughout. Do not use the spreadsheet-edited GTFS copy: some IDs were altered.
- For the reviewed V1 baseline, obtain the confirmed stop-review workbook separately. Without it the pipeline still runs, but matching coverage and output differ from our reported V1 results.
- For mapped journeys: Java 21, [OTP 2.7.0](https://github.com/opentripplanner/OpenTripPlanner/releases/tag/v2.7.0), the [Geofabrik India PBF](https://download.geofabrik.de/asia/india.html), and `osmium==4.3.2` for map preparation. Record the download date and checksums of the GTFS, PBF and OTP jar: a `latest` map can change and therefore does not guarantee identical results.

The India download used in our experiment was approximately 1.6 GB; the clipped PBF was approximately 58 MB. A full-timetable build succeeded locally with a 6 GB Java heap. Disk space, total memory and build time depend on the host; 6 GB is a tested heap setting, not a guaranteed minimum. Larger extracts previously exhausted a 5 GB heap. See [the trial note](otp-trial.md) for coverage and routing limits.

## Build the model

Create an output directory, replace the example paths below, and use an output name that does not overwrite previous work. The 1–21 October window is the training period. Do not use 25–31 October to train or select a model: it has been evaluated for an earlier candidate and is not an untouched independent test for a revised one. The confirmed workbook is optional only if you accept a different baseline.

```sh
mkdir -p data/setup
python3 src/cli.py --tickets /path/to/October-Delhi.csv --gtfs /path/to/gtfs \
  --review /path/to/confirmed-review.xlsx --confirm-review \
  --start 2026-10-01 --end 2026-10-21 --output data/setup/training.json
python3 src/index_model.py --input data/setup/training.json \
  --output data/setup/model.db --gtfs /path/to/gtfs
```

The indexer loads the training JSON in memory. Check the command's matching counts and keep the exact GTFS version with the model. This baseline groups tickets by their creation/assumed boarding hour and reports relative evidence from a potentially biased sample; it is not measured bus occupancy.

## Quick local demo without OTP

After building the index above, you can start the UI without Java, an OSM download or a running OTP server:

```sh
python3 src/api.py --database data/setup/model.db --gtfs /path/to/gtfs \
  --otp-recordings tests/fixtures/otp --port 8000
```

Open `http://127.0.0.1:8000/` and check `http://127.0.0.1:8000/health`. The recordings cover only the exact captured requests; other requests use the simplified GTFS fallback. That fallback estimates walking with straight-line distance and searches a limited set of routes, so it can miss journeys and does not provide street-network walking distances. The response's `routing_source` identifies which routing method answered. The recordings do not replace the ticket file, GTFS or model database needed to start the API. See [fixture notes](../tests/fixtures/otp/README.md) for recorded cases and their limitations.

## Build the full-timetable map graph

Create a Python environment and install map preparation dependencies using your environment's normal procedure, then run:

```sh
python3 -m pip install 'osmium==4.3.2'
python3 scripts/prepare_otp_map.py --regional /path/to/india-latest.osm.pbf \
  --output-dir data/setup/map-crop
mkdir -p data/setup/otp-graph
cp data/setup/map-crop/regional-clipped.osm.pbf data/setup/otp-graph/
```

The map-crop output directory must not exist before the preparation command. Put **one** flattened GTFS ZIP made from the same original feed in `data/setup/otp-graph/`; its GTFS `.txt` files must be at the ZIP root. For example, with `zip` installed and `/path/to/gtfs` being the directory containing those files:

```sh
zip -j data/setup/otp-graph/feed.zip /path/to/gtfs/*.txt
printf '%s\n' '{"dataImportReport":true}' > data/setup/otp-graph/build-config.json
java -Xmx6G -jar /path/to/otp-shaded-2.7.0.jar --build --save data/setup/otp-graph
```

Only build in a new graph directory; OTP writes its outputs there. Review the import report, particularly isolated stops, and test representative journeys. In one local run, zero of 6,812 GTFS stops were reported isolated; this checks street-graph linkage, not the correctness or accessibility of all walking paths. The bounding box is specific to this feed and requires rechecking if the GTFS changes. Follow OpenStreetMap attribution and licence requirements when presenting or redistributing map data.

## Run and check

In separate terminals, start OTP and the API:

```sh
java -Xmx6G -jar /path/to/otp-shaded-2.7.0.jar --load --bindAddress 127.0.0.1 --port 18080 data/setup/otp-graph
python3 src/api.py --database data/setup/model.db --gtfs /path/to/gtfs \
  --otp-endpoint http://127.0.0.1:18080/otp/gtfs/v1 --port 8000
```

Check `curl http://127.0.0.1:8000/health`, open `http://127.0.0.1:8000/`, and try the mapped API request in [the trial note](otp-trial.md). Use a service date supported by the supplied GTFS. A healthy API alone does not prove OTP, map coverage or model predictions are correct. Check a direct journey, a walking transfer, an outer-region journey and a no-route case. Current transfer-distance filtering happens after OTP's search, so it cannot guarantee all compliant alternatives are returned; walking and bus times are scheduled or map-derived estimates.
