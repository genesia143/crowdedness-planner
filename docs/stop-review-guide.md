# Reviewing ticket stop names

The review sheet lists ticket stop names that do not match exactly against GTFS stops on the same route. It uses training tickets only and sorts by the number of affected ticket rows; a row count is not necessarily a passenger count. Boarding and destination uses are listed separately. The sheet is a prioritized work list, not a random sample and not an accuracy measurement.

1. Open the CSV in a spreadsheet and leave the original ticket and GTFS files untouched.
2. Check that the ticket name and suggested GTFS stop refer to the same place **on the listed route and direction**. Directions, block letters and separate sides of a road matter. Similar spelling alone is not enough.
3. In `decision`, enter `correct`, `incorrect`, or `unsure`. If you can confidently identify the right GTFS stop ID, add it in `correct_gtfs_stop_id`; otherwise leave that field blank and explain in `notes`. When more than one candidate ID appears, identify the correct one rather than approving all of them. If unsure, leave it unresolved.
4. Save as CSV. Do not change route or ticket spelling columns: they are the lookup keys. We will validate and apply reviewed mappings in a separate step; merely editing the sheet does not yet change the model.

A suggested name may be blank because the matcher was unsure. Its absence does not mean the stop is absent from GTFS. Use the route and GTFS stop locations or trusted local knowledge to resolve it. Frequency-based prioritization improves coverage, but we also need a separate random sample to estimate matching precision.

To regenerate the sheet, use `scripts/prepare_stop_review.py --tickets <ticket.csv> --gtfs <gtfs-directory> --start 2026-10-01 --end 2026-10-21 --output data/stop-review.csv`. Data outputs are excluded from Git. The reserved test dates must not be used to build the review queue.
