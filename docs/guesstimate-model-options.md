# Guesstimates for the crowding model

This is a design note, not a calibrated model or a claim of improved accuracy. The relevant guesstimate sections were inspected selectively in the local Product Casebook (PDF pp. 52–54) and Casebook_2025 (PDF p. 58). They recommend defining the question, segmenting assumptions, using demand and supply perspectives, and sanity-checking results. Their examples are interview exercises, not evidence about Delhi's ticket sampling.

## Define the quantity

For a route, direction, segment, hour and day type, estimate the distribution of people on board per actual bus. A single ticket observation is not a full passenger count. If T is observed ticket-sample passenger-segment crossings, B is buses actually traversing the segment, and p is the proportion of all passenger-segment crossings captured by the sample, an illustrative estimate is T/(B*p). The assumptions must refer to the same route, segment, time, fleet and units. The share p includes riders absent from the sample, including pass holders if they are excluded; don't add them again. A measured B from GPS would require coverage checks; GTFS B is scheduled, not actual.

Example only: T=12, B=6 and hypothetical p=0.10, 0.25 or 0.50 yield 20, 8 or 4 passengers per bus. The rates are invented; the range is not a confidence interval and is not a Delhi finding. Ticket creation time, incomplete stop matching, nonrepresentative capture and passenger distribution across trips also affect interpretation.

## Practical use

1. Reproducibly derive observed ticket-segment counts and scheduled crossings, and track match loss.
2. Identify independent data for bus service, total ticket/passenger boardings, pass holders, capacity, and actual onboard counts, at matched route, time and population scopes. Distinguish unknown from assumed values.
3. Build explicit low/base/high sensitivity scenarios or a statistical hierarchical model, with route/day/time heterogeneity only where data can support it. Use assumptions as exploratory scenarios rather than actual occupancy. A distribution for p is a prior, not automatically evidence or a validated confidence interval.
4. Check outputs against independently observed counts and fleet capacity only when capacities refer to the same bus and measurement definition; standing space matters. Do not cap suspicious estimates silently; investigate them.
5. Compare candidates against a baseline using independent observations. The October 25–31 ticket holdout has already been inspected; it cannot serve as an untouched final test for a revised model. Ticket-based targets cannot establish actual occupancy accuracy. If no new independent data exists, document the limitation and assess only ticket-pattern agreement.
6. For commuters, continue to distinguish unavailable and weaker evidence, and do not rank cross-route physical crowding without calibration. Display the basis and uncertainty plainly.
