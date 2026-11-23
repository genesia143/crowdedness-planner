# Experimental busy-route benchmark

This training-only experiment uses the October 1–21 model; it does not read October 25–31 tickets. Run:

```sh
python3 scripts/benchmark_sensitivity.py --database data/otp-trial/model-v1-split-days.db --output data/otp-trial/benchmark-development.json
```

Among 445 eligible route-direction codes, select the six highest median rates in weekday 07:00–09:59 supported segment-hour cells. A rate is sampled ticket passengers divided by scheduled bus crossings. Each reference is the median of three route medians: the top three give 7.71 and the next three 5.19 sample passengers per scheduled crossing. This is a 48% change in reference depending on which routes were selected. The selected codes are primarily variants of route 717, so the sets are not geographically independent.

With illustrative labels below 75%, between 75% and 125%, or above 125% of the reference, 5,347 of 186,133 supported weekday segment-hour cells (2.87%) change label between references. The higher category changes for 1,398 cells: it contains 572 cells with the first reference and 1,970 with the second. Between 96% and 99% of cells fall in the lower category, suggesting that this extreme reference compresses most scores into one category. Cells are correlated; these percentages are not journey coverage or independent samples. This is not a comparison against passenger counts or an evaluation of predictive accuracy.

Conclusion: a chosen extreme busy-route reference is sensitive and does not provide adequate discrimination for useful categories. Its interpretation as packed, standing, or seats available is unsupported. A uniform reference also cannot correct unknown route-dependent sampling rates, vehicle capacity, route direction coverage, or the gap between scheduled and actual buses. Retain as an analyst experiment only; no cross-route comfort recommendation should use it without further testing, especially independent observed occupancy. A common multiplicative benchmark rescales raw rates but cannot change their cross-route ordering.
