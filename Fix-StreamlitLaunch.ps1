# Restore browser launch for: streamlit run Home.py
New-Item -ItemType Directory -Force -Path .streamlit | Out-Null
@'
[server]
headless = false
port = 8501
address = "localhost"
enableCORS = true
enableXsrfProtection = true
maxUploadSize = 50

[browser]
gatherUsageStats = false

[theme]
base = "light"
'@ | Set-Content -Encoding ascii .streamlit\config.toml
Write-Host "Updated .streamlit\config.toml. Streamlit will open the browser." -ForegroundColor Green
Write-Host "Start the app with:" -ForegroundColor Yellow
Write-Host "  streamlit run Home.py"
