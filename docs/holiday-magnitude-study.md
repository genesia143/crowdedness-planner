# Holiday exclusion and across-day magnitude: development study

This is an exploratory comparison, not a production change. It reads the October 1–21 training aggregate, the October 22–24 development aggregate (only 22–23 are the weekday target), the corresponding GTFS feed, and the training model. No October 25–31 data is read. That later week was previously evaluated, so it is not a fresh independent holdout for a revised model.

Run from the project root:

```sh
python3 scripts/holiday_magnitude_study.py --database data/otp-trial/model-v1-split-days.db --training data/otp-trial/training-v1-split-days.json --target data/otp-trial/validation-v1-split-days.json --gtfs data/otp-trial/gtfs-original --output data/otp-trial/holiday-magnitude-study.json
```

The experiment retains the originally supported weekday cells for both comparisons. In the candidate it removes the passengers **and scheduled bus crossings for those same dates**, 2 and 20 October; holidays are not reclassified as Sundays. For each segment it labels the same supported hours relative to their unweighted mean, using the illustrative ±25% threshold. The target is constructed the same way from the 22–23 October ticket-sample rates; zero observed ticket records are treated as zero where there is scheduled service. Data outages, sample bias and scheduled-versus-actual service remain unknown.

| Outcome | Original | Holidays excluded |
|---|---:|---:|
| Agreement with magnitude-defined ticket-sample target | 110,390 / 169,472 (65.14%) | 110,821 / 169,472 (65.39%) |

There were 20,590 segment groups; 8,593 of the 169,472 labels changed. These observations are correlated, use the same stop matching and GTFS in both periods, and do not measure bus occupancy. The small difference cannot establish a meaningful real-world improvement. The study fixes the same support set to isolate the rate comparison: it does not test the effect of excluding holidays on evidence thresholds or missing labels. It is therefore insufficient on its own to justify production adoption.

For a preliminary check of whether a predicted busier hour is consistently elevated, the script looks only at weekdays where that hour and at least two other supported hours have **positive** observed tickets, normalizing by each hour's aggregate scheduled crossings. Of 45,010 predicted-busier cells with at least three such days, 30,137 (66.96%) were above 1.25 times their within-day positive-hour mean on a majority of those days. This is selection-biased: days with zero tickets are excluded, and aggregate rather than per-day service is used. It must not be described as a confidence probability or as a complete test of across-day stability. A robust follow-up needs each day's scheduled service (and includes zero-ticket days where ingestion is complete), plus uncertainty and independent counts.

The daily stability check also selects the label and assesses its stability on the **same training dates**, so it is an in-sample descriptive diagnostic rather than held-out validation. The holiday comparison uses later 22–23 October development days as its target, but its original support set was selected before the holiday exclusion.
