# Quickstart: Co-op Matching and a Job Board Layout

```bash
python start.py
```

Let the importer bring in a few thousand jobs first, or use `SEED_SAMPLE_POSTINGS=true`.

## 1. Filters

1. On the jobs page search `data`
2. In the sidebar pick Summer, Ontario, Students only and the Data job type. Each choice shows a count
3. The address now has every choice. Copy it into a new tab and the same view opens
4. Turn off "also show jobs that don't say their term". The count drops
5. Sort by Term starting soonest and then by Newly added
6. Click a job. On a wide screen its details open beside the list and `?job=` is added to the address
7. Make the window 375 px wide. Tap Filters and the same sidebar opens above the results

## 2. Matching by program and grad year

1. Make a resume with "Bachelor of Engineering, Mechanical Engineering, expected graduation 2028" and a Skills line
2. Upload it on Match my resume. Program, degree and grad year fill in on their own
3. Set the term to Summer 2027 and lengths 4 and 8
4. The top matches suit mechanical engineering and each has notes like "Summer 2027 term"
5. A job that names 2026 graduates still shows, lower, with a note to check before applying

## 3. Make your resume fit

1. Open any job with a resume uploaded
2. Click Make your resume fit. Checks, edits and word lists show with no AI key

## 4. New since your last visit

1. Visit the jobs page, then wait for an import to add jobs (or run one from Admin)
2. Come back. The bar says how many are new
3. Open Get updates and copy the RSS link into a feed reader

## Tests for this feature

```bash
cd backend
pytest -q tests/ingest/test_education.py tests/ingest/test_terms.py tests/resume tests/api/test_terms_api.py tests/api/test_updates_api.py
pytest -q -m perf -s
cd ../frontend
npm test -- FilterBar PostingCard ResumePage
npm run test:e2e
```
