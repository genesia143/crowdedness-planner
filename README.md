# Delhi crowdedness-aware journey planner

This project is being developed for Problem 2. Its first goal is a reproducible backend that estimates a **relative ticket-derived demand signal** for bus segments and helps compare journeys. A UI will follow the API.

The October ticket data appears to be a thin and potentially biased sample. Its counts do not establish how many people are aboard, whether a seat is available, or actual crowding. The proposed signal and its evaluation are explained in [the backend design](docs/backend-design.md).

## Current status

An initial segment-counting baseline is implemented. The API, predictive model and demo are not implemented yet. The evaluation interface and ground truth must be confirmed with the organizers. The October tickets and static GTFS are present elsewhere in the workspace; they are not included in this project.

## Run the initial baseline

Requires Python 3.9 or newer and local copies of the ticket CSV and static GTFS directory. From the project directory:

```sh
python3 -m unittest discover -s tests -v
python3 src/cli.py --tickets /path/to/October-Delhi.csv --gtfs /path/to/gtfs --start 2026-10-01 --end 2026-10-21 --output data/training.json
```

The output contains daily sample passenger-journey counts per segment and ticket boarding hour, plus matching counts. Exact normalized stop names must match on a route and produce one unambiguous segment sequence. The output is **not** onboard load, a prediction for an individual bus, or a normalized crowding level. The full pipeline, API, validation and UI remain to be built. Avoid using October 25–31 for model development; see the design note for the proposed split.
