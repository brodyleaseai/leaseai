# Phase 8 status

**Code and runbooks: done.**  
**Live production on a custom domain: operator steps.**

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
