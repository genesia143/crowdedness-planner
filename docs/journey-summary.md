# Journey-level ticket-pattern summary

The API computes the headline in `journey_crowding_summary`; the browser displays it and provides expandable per-leg details. This summarizes existing relative labels and is not a physical occupancy, comfort score or cross-route ranking.

- If any mapped segment has a recognized `likely busier` label, show “Some stretches busier than usual,” even when other segments are unknown.
- If none is labelled busier but at least one segment or bus leg lacks a comparison, or none is labelled, show “Limited crowding information.”
- Only when every bus leg has segment details and every segment is labelled, and none is busier, show “No busier-than-usual stretches identified.” This still means only that no supported segment has that relative label, not that any bus has seats.
- Counts show labelled versus mapped stretches. Bus legs with no segment details are disclosed separately rather than being silently omitted from a percentage. A broader-window estimate is counted as a comparison and marked as weaker evidence; unavailable, unlabelled segments are never quiet by default.

The summary does not sum crowding, compare different route baselines, estimate how long a passenger is exposed to a busy segment, or infer available seats. A single flagged stretch can trigger the headline. These conservative descriptive rules are initial product choices, not calibrated comfort or occupancy predictions, and need user testing and independent data.
