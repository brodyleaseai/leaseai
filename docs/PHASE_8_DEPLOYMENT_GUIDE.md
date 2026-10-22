# Phase 8: Production Deployment & Monitoring

## Recommendation (8.1)

Keep **Supabase** for the database. Run the Streamlit app in one of two ways:

| Option | Use when | Cost |
|--------|----------|------|
| **Streamlit Community / Team Cloud** | Fastest launch, you already run locally this way | Free or Team (~$42/user/mo) for custom domain |
| **Docker on AWS App Runner or Railway** | You want your own container and health checks | About $20–80/mo to start, not $200–500 unless you add ECS+RDS+CloudFront |

Do **not** migrate off Supabase to RDS unless you outgrow it. The app is written against Supabase.

This repo includes a `Dockerfile` and `docker-compose.yml` so you can do either path.

## Streamlit Cloud

1. Push `main` to GitHub (already done).
2. In Streamlit Cloud, New app → repo `brodyleaseai/leaseai` → main file `Home.py`.
3. Add secrets (same values as `.env`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`, Stripe keys, `SENTRY_DSN`, `APP_URL`.
4. Team plan → Settings → Custom domain → `app.leaseai.co`.

## Docker (local or App Runner)

```
cp .env.production.example .env
# fill values
docker compose up --build
```

App: http://localhost:8501  
Health: http://localhost:8501/_stcore/health

AWS App Runner: push the image to ECR, create a service, port 8501, attach the env vars.

## Custom domain (8.2)

1. Buy `leaseai.com` or `leaseai.co` (you do this).
2. Cloudflare DNS:
   - Streamlit Cloud: CNAME `app` → the hostname Streamlit gives you, proxy off or follow their docs.
   - App Runner: CNAME `app` → the App Runner URL.
3. HTTPS is automatic on Streamlit Cloud and App Runner.

## Monitoring (8.3)

**Sentry (errors)**  
1. Create a project at https://sentry.io  
2. Copy the DSN into `SENTRY_DSN`  
3. Restart the app. `observability.py` initializes Sentry on boot.

**UptimeRobot (uptime)**  
1. https://uptimerobot.com → Add monitor  
2. Type: HTTPS  
3. URL: `https://YOUR_APP/_stcore/health` (or the home page)  
4. Interval: 5 minutes  
5. Alert contact: your email or Slack  

**Do not** need Datadog or CloudWatch until you are on AWS.

## Logs (8.4)

The app writes JSON lines to stdout (`observability.log_event`).  
Streamlit Cloud, Docker, and App Runner all capture stdout.

Optional: run `database_schema_performance.sql` and call `persist_log()` to keep errors in `application_logs` for 30+ days. Audit actions already go to `audit_log`.

Papertrail / Logtail: point their Docker or syslog drain at the container stdout.

## Performance (8.5–8.7)

1. Run `database_schema_performance.sql` in Supabase (indexes on `leases` + log tables).
2. Dashboard lease counts use a 45-second cache (`query_cache.py`).
3. Extractions time out at 300 seconds (`extraction_timeout.py`).
4. Optional worker: `python extraction_worker.py` after jobs are inserted into `extraction_jobs`.
5. Load smoke test (app must be running):

```
pip install requests
python load_test_smoke.py --url http://localhost:8501/_stcore/health --users 20 --requests 5
```

Targets: health under 3s, error rate under 1%. This is not a 50-user upload test; do that after production DNS is live.

## What you still do outside the repo

- Buy the domain
- Create Sentry and UptimeRobot accounts
- Paste secrets into Streamlit Cloud or the host
- Watch 30 days of uptime for the 99.5% SLA claim
