# Quickstart: Jobs From Every Field, From Public Sources

## 1. Watch real jobs come in

```bash
python start.py
```

About a minute after start the importer begins, 3 sources at a time. Make yourself admin (see
`guides/owner-handbook/`) and open Admin. Sources fill in with jobs added, updated and closed.

## 2. Run one source by hand

1. On Admin, find a Workday employer like CIBC and click Run now
2. Its history shows a new run with jobs added
3. Click Run now again. Jobs are updated, not added again

## 3. Every field

On the jobs page try the Health, Trades and Hospitality job types. Each has jobs. Turn on Students only and look
for titles ending in "(student)" or "(apprentice)" from Job Bank.

## 4. Right place

1. Search `Walmart` with Canada picked. The count is in the thousands
2. Pick Ontario. No job shows a US state

## 5. Add an employer

1. Add a line like `("Example Co", "greenhouse", "exampleco")` to `backend/seed/job_boards.py`
2. Restart. The seed sees the change and adds the source
3. Run it from Admin

## 6. Find more boards

```bash
cd backend
python -m seed.discover_boards --lists
```

## Tests for this feature

```bash
cd backend
pytest -q tests/ingest
```

All of them play back recorded replies. None call the real sites.
