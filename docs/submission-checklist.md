# Submission checklist

Status: **3 of 6 milestones complete**, with model validation and final polish still open.

1. [x] Journey evidence summary: per-leg provisional labels and missing evidence; no unsupported cross-route occupancy score.
2. [x] Model selection and freeze: inspect tuning-period label agreement, sparse evidence, timing and day types; lock configuration, inputs, model and evaluation protocol. No final-week tuning.
3. [ ] Final evaluation: after freeze, evaluate the October 25–31 holdout and report ticket-sample limitations and coverage.
4. [ ] Planner verification: representative direct and walking-transfer routes, timing, geographic coverage, 1 km search completeness and known limitations.
5. [x] Functional UI prototype: browser-tested direct and transfer journey flow, with provisional labels and evidence limitations. Final wording and polish remain dependent on validation.
6. [ ] Submission readiness: reproduce setup in a fresh environment, pin dependencies and data provenance, complete instructions and technical note, and run end-to-end checks.

Provisional labels are comparisons within a route segment across hours, not measured onboard loads. The candidate and input snapshot are frozen; the final week remains reserved for evaluation. Sunday labels are unvalidated and occupancy ground truth is unavailable.
