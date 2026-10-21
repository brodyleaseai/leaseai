# LeaseAI Phase 5B - Download All Files
# Two-Factor Authentication & Automated Backups Implementation

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LeaseAI Phase 5B: 2FA & Automated Backups" -ForegroundColor Cyan
Write-Host "Downloading 7 files..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
$files = @(
    @{Path="two_factor_auth.py"; Name="2FA Module (TOTP)"},
    @{Path="database_migration_2fa.sql"; Name="Database Migration for 2FA"},
    @{Path="pages/14_%E2%9A%99%EF%B8%8F_User_Settings.py"; LocalPath="pages/14_User_Settings.py"; Name="User Settings Page"},
    @{Path="requirements_2fa.txt"; Name="2FA Python Dependencies"},
    @{Path="auth_module.py"; Name="Updated Authentication Module"},
    @{Path="docs/AUTOMATED_BACKUP_CONFIGURATION.md"; Name="Backup Configuration Guide"},
    @{Path="docs/PHASE_5B_COMPLETION.md"; Name="Phase 5B Completion Summary"}
)

$successCount = 0
$failCount = 0

foreach ($file in $files) {
    $url = "$baseUrl/$($file.Path)"
    $localPath = if ($file.LocalPath) { $file.LocalPath } else { $file.Path }
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
Write-Host "Phase 5B Files Ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Install dependencies: pip install -r requirements_2fa.txt"
Write-Host "2. Run database migration in Supabase SQL Editor"
Write-Host "3. Restart Streamlit: streamlit run Home.py"
Write-Host "4. Navigate to User Settings page (page 14) to enable 2FA"
Write-Host "5. Review AUTOMATED_BACKUP_CONFIGURATION.md for backup setup"
Write-Host ""
Write-Host "Read docs/PHASE_5B_COMPLETION.md for full instructions!" -ForegroundColor Cyan
Write-Host ""
