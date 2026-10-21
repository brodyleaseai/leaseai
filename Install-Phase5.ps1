# LeaseAI Phase 5 Installation Script
# Downloads all Phase 5 Security Hardening files from GitHub

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LeaseAI Phase 5 Installer" -ForegroundColor Cyan
Write-Host "Security Hardening & Enterprise Readiness" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"
$localPath = "C:\Users\brody\OneDrive\Desktop\LeaseAI"

# Check if directory exists
if (-Not (Test-Path $localPath)) {
    Write-Host "Error: Directory not found: $localPath" -ForegroundColor Red
    exit 1
}

Set-Location $localPath
Write-Host "Installing to: $localPath" -ForegroundColor Green
Write-Host ""

# Files to download
$files = @{
    # Python modules
    "audit_logger.py" = "audit_logger.py"
    "run_security_scan.py" = "run_security_scan.py"
    
    # Database schema
    "database_schema_audit_security.sql" = "database_schema_audit_security.sql"
    
    # Streamlit pages (URL encoded emoji)
    "pages\12_🔒_Security_Dashboard.py" = "pages/12_%F0%9F%94%92_Security_Dashboard.py"
    
    # Documentation
    "docs\2FA_Setup_Guide.md" = "docs/2FA_Setup_Guide.md"
    "docs\Backup_and_Disaster_Recovery_Guide.md" = "docs/Backup_and_Disaster_Recovery_Guide.md"
    "docs\Data_Processing_Agreement_DPA.md" = "docs/Data_Processing_Agreement_DPA.md"
    "docs\Information_Security_Policy.md" = "docs/Information_Security_Policy.md"
    "docs\Master_Services_Agreement_MSA.md" = "docs/Master_Services_Agreement_MSA.md"
    "docs\PHASE_5_README.md" = "docs/PHASE_5_README.md"
    "docs\SOC2_Gap_Analysis.md" = "docs/SOC2_Gap_Analysis.md"
}

# Create directories if they don't exist
Write-Host "Creating directories..." -ForegroundColor Yellow
if (-Not (Test-Path "pages")) {
    New-Item -ItemType Directory -Path "pages" | Out-Null
}
if (-Not (Test-Path "docs")) {
    New-Item -ItemType Directory -Path "docs" | Out-Null
}

# Download files
$successCount = 0
$failCount = 0

foreach ($localFile in $files.Keys) {
    $remoteFile = $files[$localFile]
    $url = "$baseUrl/$remoteFile"
    
    Write-Host "Downloading: $localFile" -ForegroundColor Cyan
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $localFile -ErrorAction Stop
        Write-Host "  ✓ Success" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        $failCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Successful: $successCount files" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "✗ Failed: $failCount files" -ForegroundColor Red
}
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "✓ Phase 5 installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Run the SQL schema in Supabase:" -ForegroundColor White
    Write-Host "   - Open Supabase Dashboard → SQL Editor" -ForegroundColor Gray
    Write-Host "   - Copy contents of database_schema_audit_security.sql" -ForegroundColor Gray
    Write-Host "   - Paste and run in SQL Editor" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Install security scanning tool:" -ForegroundColor White
    Write-Host "   pip install bandit" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. View Security Dashboard:" -ForegroundColor White
    Write-Host "   - Restart Streamlit app" -ForegroundColor Gray
    Write-Host "   - Navigate to 🔒 Security Dashboard in sidebar" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Review documentation:" -ForegroundColor White
    Write-Host "   - See docs\PHASE_5_README.md for complete guide" -ForegroundColor Gray
    Write-Host "   - Review SOC2_Gap_Analysis.md for roadmap" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "⚠ Installation completed with errors." -ForegroundColor Yellow
    Write-Host "Please check the failed files and try again." -ForegroundColor Yellow
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
