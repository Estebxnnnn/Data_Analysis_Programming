# Workshop 1 — Evidence and Delivery Checklist

Status as of 14 Nov 2026. Items map to the evaluation rubric (20 points).

## A. Real queries (four validated sources with evidence — 5 pts)
- [x] `.env` with a descriptive `TCMON_USER_AGENT` and contact e-mail
- [x] `collect_samples.py` run on 2026-11-14 18:29–18:32 UTC → `samples/`, `evidence/access_log.csv`
- [x] Every source answered HTTP 200 (GDACS end-of-pages = HTTP 204, documented)
- [x] IBTrACS URLs (S1, S3) confirmed
- [x] Real response snippets in report §3.6

## B. Incremental behaviour
- [x] Poll 1 — 2026-11-14 18:28:48 UTC
- [x] Poll 2 — 2026-11-14 19:41:33 UTC (73 min later)
- [x] `evidence/poll_diff.md` generated and copied into report §3.5
- [ ] Optional third poll after the Sunday 15 Nov IBTrACS release (`poll_snapshot.py`, then `diff_snapshots.py`)

## C. Profiling (profiling and data-quality findings — 4 pts)
- [x] `notebooks/01_source_profiling.ipynb` executed top to bottom with outputs (2026-11-14 19:05 UTC)
- [x] ≥ 200 records per source (S1 312,394; S2 106; S3 and S4 full responses, smaller than 200 off-season)
- [x] 8 data-quality problems with real example records (report §4.2, `evidence/dq_examples.csv`)
- [x] 7 candidate same-event pairs (report §4.3, `evidence/overlap_pairs.csv`)
- [x] All TO VERIFY items confirmed or corrected

## D. Mapping, contract, project definition (4 + 3 + 2 pts; hazard and scope: 2 pts)
- [x] `mapping.md` / `mapping.csv` updated with the profiling results
- [x] ER diagram and `sql/001_schema_draft.sql` consistent (`peak_wind_kt` added)
- [x] `ingestion_contract.md` with verified duplicate keys and watermarks
- [ ] Architecture diagram checked against the Course Project reference architecture (document not available to the team assistant)

## E. Repository and submission
- [ ] Push to GitHub (`git status` must not list `.env` or `data/raw/` files)
- [ ] Put the repository link on the report cover (§ header) and in §8.3
- [ ] Export the report to a single PDF and submit it with the repository link
- [ ] Send the open questions (report §9.1) to the professor
