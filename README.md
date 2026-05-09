# M60 EVT REL Dashboard

## Run

- Backend API: `python api.py`
- Frontend dev: `npm --prefix frontend run dev`
- Frontend build check: `npm --prefix frontend run build:check`
- Data import (full rebuild): `python processor.py --all --rebuild`
- Legacy Flask dashboard: disabled (see `dashboard.py`, returns `410`)

## Verify

- Python tests (unittest): `python -m unittest discover -v`
- Frontend smoke test: `npm --prefix frontend test`
- Fact-table parity check: `python verify_fact_parity.py`
