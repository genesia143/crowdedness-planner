# Development-period hourly ranking diagnostic

Run the ranking diagnostic with the same clean GTFS, training index, reviewed
mappings and October 22–24 tuning records used for the development validation:

```sh
python3 scripts/validate_v1_ranking.py --database data/otp-trial/model-v1-original-gtfs.db \
  --validation data/otp-trial/validation-v1-original.json \
  --gtfs data/otp-trial/gtfs-original --output data/otp-trial/v1-ranking-report.json
```

Within each route, directed segment and day type, the script compares pairs of
hours meeting the API's provisional training support rules. For each hour,
the tuning outcome is matched sample passengers divided by scheduled
crossings, pooled across the tuning days of the corresponding type. It reports
how often the pair has the same order in training and tuning. Equal training or
tuning values are reported as ties, not successes. The concordance denominator
excludes ties. Counts refer to hour pairs, not independent passenger journeys;
nearby segments share observations and should not be interpreted as independent
statistical samples.

A zero means no *matched sample* passengers on scheduled crossings, assuming
complete ticket ingestion; it does not establish empty buses. The same stop
matching creates both sides, scheduled service may not run as planned, and
boarding-time and segment-crossing-time mismatch can bias comparisons. The
three-day tuning interval contains no Sunday, and the current weekend category
combines Saturday and Sunday in training. This checks ordering in a ticket
sample; it neither measures occupancy accuracy nor calibrates label reliability.
The final week remains sealed. Any tuning choices based on these results must be
fixed before the final evaluation.

## First tuning result

Using the original GTFS and the October 22–24 tuning data, the diagnostic
compared supported hour pairs within the same route and directed segment.
Among pairs whose training and tuning rates differed, 619,826 of 775,797
weekday pairs (79.9%) and 169,566 of 227,915 Saturday/weekend pairs (74.4%)
agreed in direction. Ties are excluded from these percentages and reported
separately by the script. These pairs are not independent: many share segments,
trips and days. The result measures consistency of the matched ticket sample,
not occupancy accuracy, confidence in individual labels, or independent test
performance. The tuning window contains no Sunday. A label needs three
supported comparison hours and other support thresholds; only 224,688 of
1,919,866 scheduled route-segment/hour/day-type cells in the training index
qualify, approximately 11.7%. This is an unweighted cell count, not the share
of journeys or riders covered.
