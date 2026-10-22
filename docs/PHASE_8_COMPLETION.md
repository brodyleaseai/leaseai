# Phase 8 status

**Code and runbooks: done.**  
**Live production on a custom domain: operator steps.**

## 8B now included

- More dashboard query caching (Home, Admin, Critical Dates, Portfolio Health, bulk client list)
- Bulk upload already processes up to 3 leases in parallel
- Extraction timeout remains 5 minutes
- Load test defaults to 50 concurrent workers against health + home
- Local run (this environment): 50 workers x 2 hits, health 100/100 in 0.006s avg, home 100/100 in 0.053s avg, 0% errors. This is page/health load, not 50 concurrent PDF uploads.
- Extra indexes for `critical_dates` (re-run the same SQL file; `IF NOT EXISTS` is safe)

## Built

- Deploy decision and steps: `docs/PHASE_8_DEPLOYMENT_GUIDE.md`
- `Dockerfile`, `docker-compose.yml`, `.streamlit/config.toml`
- Sentry + JSON logs: `observability.py` (wired in `Home.py`)
- Query cache and lease indexes
- 5-minute extraction timeout
- Optional extraction worker
- `load_test_smoke.py`
- GitHub Action to build the Docker image

## Not done in this repo (cannot be)

- Purchasing leaseai.com / leaseai.co
- Creating your Sentry / UptimeRobot accounts
- Pointing DNS
- 30-day 99.5% uptime evidence
- 50 concurrent upload load test against production
