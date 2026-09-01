The SLO module's docstring says its job is catching **silent zero** — a source that stops flowing and reports 0 rows, which reads as "nothing happened" rather than "nothing arrived". This adds the mirror case: **silent ceiling**.

## The problem

`fetch_firms_fires` caps the global VIIRS CSV at the top 5000 hotspots by FRP:

```python
fires = heapq.nlargest(5000, all_rows, key=lambda x: x["frp"])
```

The cap itself is sensible — the map cannot usefully draw every thermal anomaly on the planet. But `len(all_rows)` is discarded, so downstream `len(latest_data["firms_fires"])` returns 5000 and is indistinguishable from a real measurement. `/api/health` reports it as `"firms_fires": 5000`.

On a normal day the global 24h feed carries several times that, so an operator reads a ceiling as a total. Same shape as `empty`, opposite direction: a number that means something other than what it appears to mean.

## The change

All additive and backward compatible.

- **`_store`** — `source_totals` dict, plus `_mark_total(source, total)` and `get_source_totals_snapshot()`, mirroring the existing `source_timestamps` / `_mark_fresh` / `get_source_timestamps_snapshot` trio. A fetcher that caps records the upstream count before truncating.
- **`earth_observation`** — `fetch_firms_fires` records `len(all_rows)`; the country-enrichment path updates the figure after its own 6000 merge cap. Both caps become named constants, and the log line now reports stored-of-upstream with a `[TRUNCATED]` marker.
- **`slo.compute_status`** — optional `total_rows` parameter. When it exceeds `row_count`, the entry gains `total_rows` and `truncated: true`. A source that never caps gains **no new keys at all**, so a consumer cannot mistake absence for `truncated: false`. `compute_all_statuses` takes an optional third argument; existing two-argument callers are unaffected.
- **`routers/health`** — passes the totals snapshot through.

`row_count` is left exactly as it was. It is still the number of rows stored; the addition only lets a consumer learn that it is a floor.

## Tests

`backend/tests/test_slo_truncation.py` covers both directions, the no-total case, the unconfigured-source case, and the backward-compatible two-argument call.

Full disclosure on verification: I could not run `pytest backend/tests/` in my environment — `reverse-geocoder` and `sgmllib3k` fail to build there, and your `conftest.py` errors on your own existing tests as a result. I exercised the changed functions directly in isolation (10/10 assertions), and the patch applies cleanly on `cd6395f5`. Your CI is the real check; if it goes red I will push fixes rather than ask for a merge.

## Note

Happy to split this into "add the mechanism" and "use it in FIRMS" if you would rather review them separately, or to drop the health-endpoint wiring if you would prefer the flag stay internal for now.
