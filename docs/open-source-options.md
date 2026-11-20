# Open-source options for the planner

These are candidates for targeted testing, not selected dependencies. Verify licenses, version compatibility, data rights and maintenance before adoption.

- [pyraptor](https://github.com/lmeulen/pyraptor): lightweight Python timetable routing, including multicriteria algorithms. Trial with the Delhi feed, especially transfers, service calendars, route variants, loops, after-midnight trips and performance. Multicriteria support does not mean crowding costs are already integrated.
- [OpenTripPlanner](https://github.com/opentripplanner/OpenTripPlanner): mature GTFS and OpenStreetMap journey planner with a separate Java service. Offers a richer routing base, but adds a graph build, OSM data and operational setup. Crowd-aware routing would require separate integration or customization.
- [GTFS Validator](https://github.com/MobilityData/gtfs-validator): independent feed-quality checks before relying on schedules. Validation cannot prove that scheduled buses actually ran.
- [gtfs_functions](https://github.com/Bondify/gtfs_functions) and [Partridge](https://github.com/remix/partridge): candidates for independent schedule and frequency cross-checks; test calendar and segment semantics with the actual feed.
- [gtfs-segments](https://github.com/UTEL-UIUC/gtfs_segments): a possible geometry and segment cross-check. Its standard traversal summary is for a busiest day; it is not automatically our per-date, per-hour denominator.
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz): potential speedup for route-conditioned name candidates, not a guarantee of correct matches. Review a labelled sample and pin a version compatible with our Python environment.
- [DuckDB](https://github.com/duckdb/duckdb): promising for efficient aggregation and smaller intermediate data. Benchmark against our current pipeline before migrating.
- [UrbanTrips](https://github.com/EL-BID/UrbanTrips): useful methodological reading. Its pipeline and dependencies are broader than our immediate origin–destination ticket data; inspect its license and requirements before reuse.

Suggested next step: compare pyraptor and OpenTripPlanner on the same small set of Delhi trips, and cross-check scheduled segment counts against an independent GTFS tool. Keep routing separate from our crowding signal so either engine can be replaced without changing the model.
