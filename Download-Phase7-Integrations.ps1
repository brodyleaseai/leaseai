# LeaseAI Phase 7 - Download All Integration Files
# Run this script from your LeaseAI project directory

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LeaseAI Phase 7: Native API Integrations" -ForegroundColor Cyan
Write-Host "Downloading 8 files..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
$files = @(
    @{Path="integrations/base.py"; Name="Integration Framework Base"; Url="integrations/base.py"},
    @{Path="integrations/yardi.py"; Name="Yardi Voyager Integration"; Url="integrations/yardi.py"},
    @{Path="integrations/mri.py"; Name="MRI Software Integration"; Url="integrations/mri.py"},
    @{Path="integrations/quickbooks.py"; Name="QuickBooks Online Integration"; Url="integrations/quickbooks.py"},
    @{Path="integrations/docusign.py"; Name="DocuSign Integration"; Url="integrations/docusign.py"},
    @{Path="integrations/notifications.py"; Name="Slack/Teams Notifications"; Url="integrations/notifications.py"},
    @{Path="pages/13_Integrations.py"; Name="Integrations Management UI"; Url="pages/13_%F0%9F%94%8C_Integrations.py"},
    @{Path="docs/INTEGRATIONS_SETUP_GUIDE.md"; Name="Integrations Setup Guide"; Url="docs/INTEGRATIONS_SETUP_GUIDE.md"}
)

$successCount = 0
$failCount = 0

foreach ($file in $files) {
    $url = "$baseUrl/$($file.Url)"
    $localPath = $file.Path
    $displayName = $file.Name
    
    # Create directory if needed
    $dir = Split-Path -Parent $localPath
    if ($dir -and !(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    Write-Host "Downloading: $displayName..." -NoNewline
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $localPath -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Download Complete!" -ForegroundColor Cyan
Write-Host "Success: $successCount files" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "Failed: $failCount files" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Phase 7 Integration Files Ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Review docs/INTEGRATIONS_SETUP_GUIDE.md for setup instructions"
Write-Host "2. Configure integrations in the Integrations page (page 13)"
Write-Host "3. Test connections to each service"
Write-Host ""
