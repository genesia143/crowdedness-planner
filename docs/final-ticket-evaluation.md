# October 25–31 ticket-sample evaluation

The earlier Sunday broader-window candidate was selected and its inputs fingerprinted before this evaluation. It was built using October 1–21, with October 22–24 used for development. The one-time target was produced for October 25–31 with the reviewed route-stop mappings and without fuzzy matching. No data from October 25–31 was used to train that candidate. Its local target, report and frozen manifest remain in ignored `data/otp-trial/`; the input fingerprints do not by themselves prove how the artifacts were generated.

**The final week has now been inspected. It is not an untouched independent test for a revised model.** Later routing/API edits changed the fingerprinted source; the old snapshot is a historical record, not a fingerprint of the current checkout. Preserve it and create a new snapshot when a future evaluation policy and candidate are fixed.

The target contained 615,028 in-period ticket records; 339,072 matched the route and ordered-stop rules. The figures below compare the candidate's relative three-band labels against labels derived from later ticket-sample ranks within the same route segment and day type. They are conditional on supported and evaluated hours and are not accuracy against observed people on buses, seats, or physical occupancy. Different hours and segments share passenger journeys and are correlated.

| Day type | Evaluated segment-hours | Same label | Agreement |
|---|---:|---:|---:|
| Weekday | 169,521 | 112,657 | 66.46% |
| Saturday | 27,521 | 15,068 | 54.75% |
| Sunday | 126,275 | 54,051 | 42.80% |

Sunday includes 109,613 broader-window hours, with 46,274 same-label comparisons; the remaining 16,662 strict-hourly hours had 7,777 same-label comparisons. These populations and reference hours differ, so their agreement rates do not measure a causal improvement from the fallback. The test sample does not validate whether routes are comparable or which journey is most comfortable. Labels describe within-segment relative ticket patterns, and near-zero sample values do not prove empty buses. Scheduled crossings are not observed service; missing riders, match failures, ticket timestamps and destination assumptions can introduce bias.

The evaluator's reported coverage is weighted by matched sample passenger-segments, not people or journeys, and excludes or separately counts unscheduled samples. A single passenger journey contributes multiple segment observations. See `scripts/evaluate_final_v1.py` for exact metrics and [model freeze](model-freeze.md) for provenance limitations. Independent review, comparisons to simple baselines on a suitably independent dataset, and actual passenger-count calibration remain open. Do not change model parameters after seeing this report and present the same week as an untouched holdout.
