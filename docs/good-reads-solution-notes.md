# Background reading: implications for the Delhi journey planner

Status: initial targeted review, 22 November 2026. This is not a cover-to-cover review. Page references are to the editions the team consulted; the books themselves are not part of this repository. Two scanned documents need OCR or visual reading: Mobility Language Matters and Urban Transit Operations, Planning and Economics. The long textbooks and thesis were searched and relevant passages inspected selectively. The psychology and team-motivation books were indexed but not reviewed closely enough to guide model changes.

## Implications for the current solution

1. **Separate observed passenger load from a ticket-based signal.** *Vuchic, Urban Transit Systems and Technology*, pp. 166–170 and 210, discusses passenger loads and load factor in relation to the spaces offered and their variation along a route. Our digitally mediated ticket sample per scheduled crossing is neither actual passengers aboard nor a load factor. Keep a relative comparison and make its scope and missing evidence clear; do not infer seats or standing room without independent passenger counts and reliable capacity information.
2. **Describe the complete journey.** The same Vuchic book (p. 288) discusses minimizing transfer walking. *Urban Geography: A Global Perspective*, pp. 419–420, distinguishes mobility from accessibility and discusses the pedestrian environment. Show access, transfer and egress walks plus waits and bus time. A walking route inferred from OpenStreetMap does not establish safety, footpath quality or wheelchair accessibility. The simplified fallback uses estimated distances, not a mapped walking route.
3. **Test frequency, reliability and outer areas.** *Better Buses, Better Cities*, pp. 33–34 and 45, discusses coverage versus frequency and bus bunching. Nearby stops and a static schedule alone do not demonstrate adequate or reliable service. Test off-peak and outer-region examples, show schedule-based timing as such, and investigate GPS-derived service and headways only if appropriate data can be verified.
4. **Make uncertainty understandable.** *Norman, The Design of Everyday Things*, pp. 20–25, 32–33 and 38–41, motivates visibility, feedback and clear mental models. Explain in plain language whether a stretch is unsupported, based on a broader time window, or supported by the stricter hourly rule. Test the wording with users; a coloured marker must not be mistaken for a live observation or a cross-route load ranking.
5. **Keep missing values separate from zero.** *Tidy Data*, pp. 1, 3–4 and 9–10, discusses observations, variables and missing values. Preserve separately the ticket observations, scheduled route-segment-day-hour exposures, matching outcomes, and predictions. Zero matched tickets can only be interpreted as a sample count under an ingestion assumption; an unavailable label is not a quiet bus.
6. **Frame future policy analysis around opportunities.** *Pereira (2018 thesis), Distributive Justice and Transportation Equity*, pp. 3–4, discusses access to jobs, education and health and sensitivity to analytical choices. A Delhi policy view could compare scheduled travel-time access across areas and time thresholds, but this requires independently sourced opportunity and population datasets. The thesis's results for Rio are not evidence about Delhi.
7. **Support accessible information.** *Improving Public Transport White Paper*, pp. 6 and 15, discusses information barriers and users' needs. Use plain-language explanations and accessible controls; user-test the interface with people with varied needs. *The Traffic Hierarchy*, pp. 3–4 and 8–11, is an advocacy perspective on prioritising access and walking/public transport, not evidence of Delhi street conditions.

## What these readings do not establish

None independently validates Delhi's ticket matching, the Sunday broader-window rule, a universal ticket scale-up factor, actual bus occupancy, pedestrian safety, or live service. The one-time October 25–31 ticket-sample evaluation has now been run; that week is no longer an untouched test for another model. The Sunday candidate's held-out three-band agreement was approximately 42.8% across the evaluated hours; this is agreement with ticket-derived within-segment ranks, not accuracy against observed occupancy. Review the evaluation and compare appropriate baselines before making claims about usefulness.

## Suggested work sequence

- Verify the final evaluator and communicate coverage and agreement with precise denominators, including an independent baseline and limitations.
- Test users' understanding of the colour legend, missing-data and broader-window wording, and walking/waiting details.
- Validate representative peak, off-peak, transfer and outer-area journeys; distinguish mapped from straight-line walking.
- Investigate independent passenger counts, capacity and actual service data before estimating physical load or cross-route crowding.
- For a future policy dashboard, source and validate opportunity/population data and expose sensitivity to time threshold and geographic scale.

## Reading still required

- OCR or visually review Mobility Language Matters (100 scanned pages) and Urban Transit Operations, Planning and Economics (332 scanned pages).
- Continue a full reading of the remaining long books and thesis if the goal is a comprehensive literature synthesis. Findings above come from targeted sections, not exhaustive reviews.
