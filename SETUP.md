# Run the Delhi bus journey planner locally

This guide starts from a fresh clone and runs the UI and API on your computer. The **quick setup** does not require OpenTripPlanner (OTP), Java or a map download. It uses a limited built-in journey planner: its walks are estimates and it may miss routes or transfers. For the full map-based router, follow the last section.

## Fast path: published model release

Clone the repository, activate a Python 3.9+ virtual environment as in step 2, and run:

```sh
python3 scripts/fetch_release.py
python3 src/api.py --database data/release/model.db --gtfs data/release/gtfs --port 8000
```

Open http://127.0.0.1:8000/. The downloader checks SHA-256 hashes and refuses to overwrite an existing model or GTFS folder. This runs the limited built-in router; for full street-network routing, build and run OTP as described in step 7. Downloading and running a released derived model remains subject to the applicable data terms.

The steps below use a macOS or Linux terminal. Windows users can run the same commands in a suitable Unix-like shell; the Windows virtual-environment command is shown below. This setup has been exercised on the development Mac, but has **not** been independently verified on a fresh machine.

## 1. Obtain the required files

The repository does **not** contain the ticket data, GTFS feed, reviewed workbook, trained model or OTP graph. Obtain the first two inputs separately from an authorised source; the reviewed mapping CSV is included:

1. The October mobile e-ticket CSV, named `October-Delhi.csv` below.
2. The **original, unedited** Delhi static GTFS feed, extracted into a folder containing `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt` and the other feed files directly. Do not use a spreadsheet-edited copy: IDs can change.
3. The reviewed stop-name mappings in this repository at `data-reference/reviewed-stop-mappings.csv`. A confirmed workbook can also be supplied instead.

Keep the separately supplied data outside Git and share it only where you have permission. If you have received a compatible prebuilt model database, you can skip the ticket CSV and model-building steps, but you **still need the matching GTFS feed**.

## 2. Install prerequisites and clone

Install Git and Python **3.9 or later**. Python 3.9.6 was used for the documented local rebuild; Python 3.15 produced a test error in an earlier check. Then run:

```sh
git clone https://github.com/genesia143/crowdedness-planner.git
cd crowdedness-planner
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, create the environment with `py -3 -m venv .venv` and activate it with `.venv\Scripts\Activate.ps1`; use `python` in place of `python3` below. The core model and API use Python's standard library; no `pip install` is required for the quick setup.

## 3. Put the inputs in place

Create the folders:

```sh
mkdir -p data/input/gtfs data/setup
```

Copy the files you obtained into this layout:

```text
crowdedness-planner/
  data/
    input/
      October-Delhi.csv
      gtfs/
        stops.txt
        routes.txt
        trips.txt
        stop_times.txt
        ... other GTFS files ...
    setup/
```

If your GTFS ZIP contains a parent folder, copy the `.txt` files from that folder into `data/input/gtfs/` rather than leaving an extra directory level. If a compatible `model.db` was supplied, place it at `data/setup/model.db`.

## 4. Run the checks

From the repository root:

```sh
python3 -m unittest discover -s tests -v
```

The command should finish with `OK`. It tests code with test fixtures; a passing test suite alone does not prove that your local datasets are correct or that crowding estimates are accurate.

## 5. Build the model, unless you received a compatible one

Run these two commands from the repository root. Building and indexing the full dataset can take time and memory; the indexer loads the training JSON into memory.

```sh
python3 src/cli.py --tickets data/input/October-Delhi.csv --gtfs data/input/gtfs \
  --review data-reference/reviewed-stop-mappings.csv --confirm-review \
  --start 2026-10-01 --end 2026-10-21 --output data/setup/training.json
python3 src/index_model.py --input data/setup/training.json \
  --output data/setup/model.db --gtfs data/input/gtfs
```

The included CSV contains accepted mappings from the reviewed workbook. Use the **same GTFS** when building the model and running the API. The 25–31 October tickets are not used for training or selecting a model; that period has already been evaluated for an earlier candidate and is not an untouched test for a revised model.

## 6. Start the quick local planner

```sh
python3 src/api.py --database data/setup/model.db --gtfs data/input/gtfs --port 8000
```

Leave this terminal open. In your browser, open **http://127.0.0.1:8000/**. Search for an origin and destination, select a departure date covered by the GTFS feed, then select **Find journeys**. To use the map, select **Show on map** on an option; map tiles and Leaflet require internet access. With the quick planner, dashed map lines can be straight-line approximations.

The API health check is at **http://127.0.0.1:8000/health** and should return `{"status": "ok"}`. For example, in a second terminal:

```sh
curl 'http://127.0.0.1:8000/health'
curl -G 'http://127.0.0.1:8000/journeys/mapped' \
  --data-urlencode 'from_lat=28.648875' --data-urlencode 'from_lon=77.318377' \
  --data-urlencode 'to_lat=28.6323' --data-urlencode 'to_lon=77.2165' \
  --data-urlencode 'departure=2026-10-22T18:00:00+05:30' \
  --data-urlencode 'max_transfer_walk=1000'
```

The example date is for routing and must be supported by your GTFS feed. The API's `routing_source` identifies the router used. If the quick planner does not find an option, try another time or nearby stops; absence of an option does not prove no service exists. To stop the server, return to its terminal and press **Ctrl+C**.

The UI's crowd indicators are **experimental mobile-ticket pressure estimates**, not measured onboard loads or seat availability. They assume comparable app use across routes and use scheduled rather than observed bus service; see the [technical reference](docs/technical-reference.md#time-and-comfort-comparison) for the assumptions and limitations.

## 7. Optional: run with the full map-based router

For street-network walking routes and the fuller OTP search, follow [docs/setup.md](docs/setup.md#build-the-full-timetable-map-graph) to obtain Java 21, OTP 2.7.0 and an OpenStreetMap extract, prepare the map, build the graph using the same GTFS feed, and run OTP. The documented local graph build used a 6 GB Java heap; the total machine memory needed is higher, and build time and disk requirements vary. Once OTP is running on port 18080, start the API in another terminal:

```sh
python3 src/api.py --database data/setup/model.db --gtfs data/input/gtfs \
  --otp-endpoint http://127.0.0.1:18080/otp/gtfs/v1 --port 8000
```

The full router is also bounded: applying the transfer-walking limit after its search can omit suitable alternatives. See [docs/otp-trial.md](docs/otp-trial.md) for details.

## Troubleshooting

- **`No such file` or model database not found:** run from the cloned repository root and check the paths and file names in step 3.
- **Old or unknown day-type scheme:** rebuild the model and index using the current code and the steps above.
- **Port already in use:** start the API with another port, for example `--port 8001`, and open that port in your browser.
- **Page cannot connect:** check the server terminal for an error and confirm the server is still running.
- **Map does not load:** check internet access; Leaflet and map tiles are external. Journey search does not require the map to load.
- **No street-network routing:** the quick setup uses a simplified fallback. Start OTP and supply `--otp-endpoint` as described in step 7.
