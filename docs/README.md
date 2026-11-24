# Documentation

## Start here

- [Technical note](submission-note.md): the problem, method, checks and limitations
- [Checks against known patterns](known-patterns.md): peaks, weekday vs weekend, busy corridors
- [Final ticket evaluation](final-ticket-evaluation.md): the one-time held-out week (25–31 October)
- [Baseline comparison](baseline-comparison.md): stretch labels against route-wide, citywide and chance predictors
- [Technical reference](technical-reference.md): API endpoints, pipeline options and the journey estimator
- [Setup](../SETUP.md) and the [full-router setup](setup.md)

## Model and its validation

- [Backend design](backend-design.md) and [model freeze](model-freeze.md)
- [Development validation](v1-validation.md), [label agreement](v1-label-validation.md), [ranking stability](v1-ranking-validation.md), [rotating weeks](rotating-week-development.md)
- [Separate Saturday and Sunday](separate-days-analysis.md), [Sunday wider window](sunday-window-experiment.md), [support thresholds](v1-support-sensitivity.md), [coverage thresholds](coverage-threshold-study.md)
- [Proposed improvements](proposed-model-improvements.md) and the [experiments run on them](parallel-model-experiments.md): [holidays and magnitude labels](holiday-magnitude-study.md), [smoothing](smoothing-development-experiment.md)
- [Timing gaps](timing-gap-reliability.md), [benchmark sensitivity](benchmark-sensitivity.md), [V1 vs V2 matching](v1-v2-comparison.md)
- [Field check protocol](field-study/protocol.md) and [guesstimate options](guesstimate-model-options.md) for future calibration

## Journeys and routing

- [Journey crowd estimate evaluation](journey-pressure-evaluation.md) and [200-search coverage audit](journey-coverage-audit-200.md)
- [Journey summary rules](journey-summary.md), [same-route alternatives](same-route-alternatives.md), [later-departure search](journey-search-validation.md)
- [OpenTripPlanner trial](otp-trial.md) and [open-source options considered](open-source-options.md)

## Process

- [Stop review guide](stop-review-guide.md), [reproducibility check](reproducibility-check.md), [submission checklist](submission-checklist.md), [background reading](good-reads-solution-notes.md)
