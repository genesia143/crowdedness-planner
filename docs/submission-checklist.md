# Submission checklist

Status: **2 of 6 milestones complete**. The previous freeze and final-week evaluation are historical; subsequent application changes mean the current release needs a fresh fingerprint and review. The final week must not be used for training or model selection.

1. [x] Journey evidence summary: per-leg provisional labels and missing evidence; no unsupported cross-route occupancy score.
2. [ ] Release freeze: fingerprint and review the current source, dependencies, input data and model together. The prior candidate was frozen before evaluation, but is not a fingerprint of this release.
3. [ ] Evaluation review: the October 25–31 report and its limitations are documented in [the evaluation note](final-ticket-evaluation.md); independent review of its provenance and interpretation remains.
4. [ ] Planner verification: representative local journeys have been exercised, including walking and an outer-region journey. Complete geographic coverage and finding every option within the 1 km transfer limit are not guaranteed, and the potential quieter alternative has not appeared in the real examples checked.
5. [x] Functional UI prototype: local browser checks cover journey search, time budgets, walking and evidence limitations. Real user testing is outside this project's scope by decision.
6. [ ] Submission reproducibility: an isolated Python environment rebuilt the model exactly on the same machine, as documented in [the reproducibility check](reproducibility-check.md). A separate machine, access to the excluded input data and complete routing setup remain to be verified.

Provisional labels are comparisons within a route segment across hours, not measured onboard loads. The revised candidate was evaluated against the final week; that week is no longer untouched and must not be reused as independent evaluation for another model. Occupancy ground truth remains unavailable.
