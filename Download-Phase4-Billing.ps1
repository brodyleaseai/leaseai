# LeaseAI Phase 4 - Billing files
# Run from your LeaseAI project directory
# Uses Python to write emoji page names so Streamlit does not see duplicates

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LeaseAI Phase 4: Stripe Billing" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"

$plain = @(
    @{Url="payment_integration.py"; Path="payment_integration.py"; Name="Stripe billing service"},
    @{Url="usage_limits.py"; Path="usage_limits.py"; Name="Usage limits"},
    @{Url="stripe_webhook_handler.py"; Path="stripe_webhook_handler.py"; Name="Webhook handler"},
    @{Url="database_schema_billing.sql"; Path="database_schema_billing.sql"; Name="Billing SQL schema"},
    @{Url="requirements_billing.txt"; Path="requirements_billing.txt"; Name="stripe package"},
    @{Url="Home.py"; Path="Home.py"; Name="Home with Billing button"},
    @{Url="docs/STRIPE_SETUP_GUIDE.md"; Path="docs/STRIPE_SETUP_GUIDE.md"; Name="Stripe setup guide"},
    @{Url="docs/PHASE_4_COMPLETION.md"; Path="docs/PHASE_4_COMPLETION.md"; Name="Phase 4 summary"}
)

$successCount = 0
$failCount = 0

foreach ($file in $plain) {
    $dir = Split-Path -Parent $file.Path
    if ($dir -and !(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Write-Host "Downloading: $($file.Name)..." -NoNewline
    try {
        Invoke-WebRequest -Uri "$baseUrl/$($file.Url)" -OutFile $file.Path -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
}

Write-Host "Updating emoji-named pages via Python..." -NoNewline
$py = @'
import urllib.request
base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
files = [
    ("pages/15_%F0%9F%92%B3_Billing.py", "pages/15_\U0001f4b3_Billing.py"),
    ("pages/1_%F0%9F%93%A4_Upload_Lease.py", "pages/1_\U0001f4e4_Upload_Lease.py"),
    ("pages/4_%F0%9F%93%8A_Admin_Dashboard.py", "pages/4_\U0001f4ca_Admin_Dashboard.py"),
    ("pages/7_%F0%9F%91%A5_Client_Portal.py", "pages/7_\U0001f465_Client_Portal.py"),
    ("pages/9_%F0%9F%93%A6_Bulk_Upload.py", "pages/9_\U0001f4e6_Bulk_Upload.py"),
]
for url_path, dest in files:
    urllib.request.urlretrieve(base + "/" + url_path, dest)
print("OK")
'@
try {
    python -c $py
    $successCount += 5
}
catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    $failCount++
}

Write-Host ""
Write-Host "Success batches complete. Failed: $failCount" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "1. pip install -r requirements_billing.txt"
Write-Host "2. Run database_schema_billing.sql in Supabase"
Write-Host "3. Add Stripe keys - see docs/STRIPE_SETUP_GUIDE.md"
Write-Host "4. streamlit run Home.py  then open Billing"
Write-Host ""
