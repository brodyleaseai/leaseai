# LeaseAI Phase 8 files - run from the LeaseAI directory

Write-Host "Downloading Phase 8 production files..." -ForegroundColor Cyan
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
$files = @(
    @{U="Dockerfile"; P="Dockerfile"},
    @{U="docker-compose.yml"; P="docker-compose.yml"},
    @{U=".dockerignore"; P=".dockerignore"},
    @{U=".streamlit/config.toml"; P=".streamlit/config.toml"},
    @{U=".env.production.example"; P=".env.production.example"},
    @{U="observability.py"; P="observability.py"},
    @{U="query_cache.py"; P="query_cache.py"},
    @{U="extraction_timeout.py"; P="extraction_timeout.py"},
    @{U="extraction_worker.py"; P="extraction_worker.py"},
    @{U="load_test_smoke.py"; P="load_test_smoke.py"},
    @{U="database_schema_performance.sql"; P="database_schema_performance.sql"},
    @{U="requirements_production.txt"; P="requirements_production.txt"},
    @{U="docs/PHASE_8_DEPLOYMENT_GUIDE.md"; P="docs/PHASE_8_DEPLOYMENT_GUIDE.md"},
    @{U="docs/PHASE_8_COMPLETION.md"; P="docs/PHASE_8_COMPLETION.md"},
    @{U="Home.py"; P="Home.py"},
    @{U="config.py"; P="config.py"}
)
New-Item -ItemType Directory -Path ".streamlit" -Force | Out-Null
New-Item -ItemType Directory -Path "docs" -Force | Out-Null
foreach ($f in $files) {
    Write-Host $f.P
    Invoke-WebRequest -Uri "$base/$($f.U)" -OutFile $f.P
}
Write-Host "Done. Next: pip install -r requirements_production.txt" -ForegroundColor Green
Write-Host "Then run database_schema_performance.sql in Supabase." -ForegroundColor Yellow
