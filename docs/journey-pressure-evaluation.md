# Experimental journey pressure: coverage and plausibility

The 200 fixed searches in [the original audit](journey-coverage-audit-200.md) were rerun using the same GTFS stop pairs and dates. The same 199 searches returned options, all 200 requests used OTP, and all three routing offsets completed. No October 25–31 ticket records were read to fit or select these fallbacks. The model and GTFS inputs are the same as the original audit.

| Option-level outcome | Original stretch labels | Experimental journey score |
| --- | ---: | ---: |
| At least some information | 602 of 1,102 (54.6%) | 958 of 1,102 (86.9%) |
| No information | 500 of 1,102 (45.4%) | 144 of 1,102 (13.1%) |

These measures are not identical: the original count means at least one stretch label, while the new score requires an estimate for every bus leg and combines them. Of the 958 new scores, 942 received a lower/middle/higher label relative to other options in that search; 16 had a score but no distinct score to compare it with. The 90% target was not reached. Of the 958 scored options, 687 used at least one route-wide fallback, including 267 which used an all-hours or all-days fallback; 62 of those used the all-days fallback. Fallbacks are not independently validated.

| Day type | Scored options | All eligible options | Coverage |
| --- | ---: | ---: | ---: |
| Weekday | 707 | 813 | 87.0% |
| Saturday | 122 | 145 | 84.1% |
| Sunday | 129 | 144 | 89.6% |

For 197 of 199 searches with options, at least one option had a score; that does not imply every option was scored. The UI initially shows up to three options, and these statistics cover all eligible options including those behind “show more.” The randomly sampled stops are not a sample of actual travel demand and options within each search are correlated.

## Heuristic checks, not accuracy measurement

For four selected origin–destination pairs, the fastest option was queried at Monday 08:00 and 13:00, and Saturday and Sunday 08:00. The raw model score at Monday peak was higher than Monday off-peak for all four. Saturday was lower than Monday peak for three of four; Sunday was lower for all four. On Lajpat Nagar–Hauz Khas, Saturday's score was 0.481 versus Monday's 0.367, contrary to the simple weekend assumption. The selected bus route was D-046UP at both times. These are not observed bus loads, and GTFS assumes scheduled service. Four convenience-selected pairs are not representative, and fastest routes differed in some time comparisons.

The displayed labels compare only options within each search. For Anand Vihar–Shivaji Stadium, the fastest option was labelled higher for both weekday peak and off-peak even though its raw score dropped from 1.677 to 0.337: the competitors also change. A “higher” label therefore does not mean an absolute peak or a crowded bus, and labels from separate searches must not be compared as a fixed scale. Labels were not forced to match these heuristics.

The sample cannot establish actual accuracy: passenger counts, app adoption rates by route, ticket timing and true bus service are unverified. One reason for a remaining gap was route 976UP, which has scheduled crossings in the index but no matched mobile-ticket signal in the training period. A citywide substitute could manufacture a score without evidence on that route; the current implementation leaves such cases unavailable.

Results are retained locally in `data/otp-trial/journey-pressure-broad-200.json` and `data/otp-trial/journey-heuristic-check.json`, which are excluded from Git. Reproduction scripts are [coverage audit](../scripts/audit_journey_coverage.py) and [heuristic checks](../scripts/check_journey_heuristics.py). The model computation is in [journey_pressure.py](../src/journey_pressure.py); assumptions and their limitations are in the README.
