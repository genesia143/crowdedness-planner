# Bounded later-departure search: local verification

The mapped API searches the requested departure plus 10 and 20 minutes, combines distinct itineraries, and recalculates waiting from the original departure. It selects returned arrivals within the user-configured time budget after the fastest returned arrival, and optionally before the requested latest arrival. This is a bounded heuristic: it is not an exhaustive search, cannot guarantee the actual fastest or most comfortable route, and the 10/20-minute offsets are fixed even if the time budget differs. The 1 km transfer-walk limit filters router results after search, which may hide valid alternatives. The interface reports incomplete offset searches.

Local OTP 2.7 test, October 22, 2026 and a 20-minute budget, using recorded example coordinates and the candidate model:

| Request | Distinct returned | Within 20 minutes | Searches completed |
|---|---:|---:|---|
| Anand Vihar–Shivaji Stadium, 18:00 | 18 | 4 | 0, 10, 20 min |
| Lajpat Nagar–Hauz Khas, 09:00 | 15 | 4 | 0, 10, 20 min |
| Narela–Kashmere Gate, 07:30 | 53 | 12 | 0, 10, 20 min |
| India Gate–Saket, 10:00 | 39 | 6 | 0, 10, 20 min |

These are schedule-based routing smoke tests, not proof routes are feasible, complete, accessible, or correctly timed in reality. The India Gate–Saket returned options included both first- and last-mile walk legs. Recorded-fixture regression tests also check late and outer-region examples; their old transfer-walk-zero case does not actually exclude an option. Real rider usability testing, additional dates and geographies, transfer-limit completeness, and clean-machine verification remain open.

Comfort remains unranked: cross-route physical comfort and seat availability have not been validated. A sensitivity test of the proposed busy-route benchmark is in [benchmark-sensitivity.md](benchmark-sensitivity.md). No October 25–31 data was used for this routing check.
