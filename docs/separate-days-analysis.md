# Separate Saturday and Sunday: development results

The October 1–21 training window contains three Saturdays and three Sundays.
The old four-scheduled-day support rule would make every separate weekend
label unavailable. The experimental split model instead requires at least
three matched days, ten sampled passengers and three scheduled days for a
Saturday or Sunday hour, while weekdays retain four scheduled days. Three
supported hours and two distinct rates are still required for a label. The
three-day weekend rule is a feasibility adjustment, not validated confidence.

The clean-GTFS split model matched the same 916,872 of 1,672,406 training
tickets as the prior V1. On October 22–24 tuning data it provided provisional
labels for 1,395,442 of 2,050,630 matched sample passenger-segments (68.0%);
this counts segments, excludes unmatched tickets and is not journey or rider
coverage. Sunday has no tuning observations.

For a like-for-like comparison on the 27,516 Saturday segment-hours for which
both models had supported labels and a meaningful common target, the earlier
pooled-weekend model agreed with tuning-sample relative labels 51.6% of the
time, compared with 56.4% for the Saturday-specific model. The common target is
based on one Saturday of matched ticket data, segment-hours are correlated,
and the models use different comparison-hour pools and support rules. These
numbers do not prove actual crowding accuracy or establish Sunday performance.
Run `scripts/compare_saturday_models.py` for the comparison.

A separate timing-gap analysis found that suppressing labels on routes with
more than a 5% training mismatch removes substantial evidence for a small
increase in sample-label agreement. The filtering changes the population and
is not causal; see [the timing-gap analysis](timing-gap-reliability.md). The
current prototype retains segment-level timing cautions instead of suppressing
whole routes. No final-week data was used.
