# Independent bus occupancy field check

Purpose: assess whether the planner's recorded predictions agree with independent observations. A convenience sample of 30–50 buses is exploratory, not a network-wide accuracy guarantee.

## Before observing

Choose several routes and both directions across peak and off-peak periods, with a mix of places and day types. Record locations and time windows before collecting results. Freeze the candidate model and save predictions and their timestamps before observing each bus, avoiding selection based on the eventual result. Document whether the prediction corresponds to a particular bus or a route/time/segment average; compare like with like. Plan around the already-used October 25–31 holdout rather than treating it as fresh data. Historical-ticket-derived predictions made for a later date are retrospective-pattern forecasts, not live counts.

Agree category definitions in advance. When safe and feasible, count people aboard and separately note available seated and total capacity from a reliable source; otherwise record a coarse observation with clear definitions, for example seats available, all seats occupied with some standing, or densely crowded. Do not guess capacity or silently map relative labels to absolute occupancy. A bus interior may not be fully visible: record visibility and mark uncertain or missing observations unknown. Never photograph passengers or record identifying information.

## For each observation

Record date, local time, route, direction, stop or segment, vehicle/trip identifier if lawfully and clearly visible, vehicle type if known, whether observing boarding or on-board at the segment, approximate on-board headcount or predefined category, observed capacity and its source if known, visibility/uncertainty, and any service disruption. Record the contemporaneous model result, model version, evidence tier, and prediction timestamp separately. Do not infer bus load from boarding counts at a single stop.

## Analysis

Report all observations and missing values. Separate route/time-level model outputs from per-trip observations and avoid treating them as identical: summarize observed buses within each matching route, direction, segment and time where feasible. Show agreement/confusion table only when predicted and observed labels have the same documented meaning. Compare against a simple baseline and report sample counts by route/time. Note non-random selection, observer error, repeated buses or shared conditions, and the absence of guaranteed representativeness. Seek suitable operator or organizer data for independent calibration and a separate larger evaluation.
