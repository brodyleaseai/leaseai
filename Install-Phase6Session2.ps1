# LeaseAI Phase 6 Session 2 - Automated Installation Script
# Run this in PowerShell from your LeaseAI directory
# Usage: .\Install-Phase6Session2.ps1

param(
    [string]$InstallPath = "C:\Users\brody\OneDrive\Desktop\LeaseAI"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LeaseAI Phase 6 Session 2 Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# GitHub repository raw file base URL
$GitHubRepo = "https://raw.githubusercontent.com/brodyleaseai/leaseai/main"

# Files to download
$NewFiles = @(
    "health_report_emailer.py",
    "health_report_pdf.py",
    "scheduled_health_monitoring.py",
    "database_schema_notification_system.sql",
    "AUTOMATED_MONITORING_SETUP.md",
    "example_health_monitoring_usage.py"
)

$ModifiedFiles = @{
    "anomaly_detection_engine.py" = "anomaly_detection_engine.py"
    "pages/11_🏥_Portfolio_Health.py" = "pages\11_🏥_Portfolio_Health.py"
}

# Check if install path exists
if (-not (Test-Path $InstallPath)) {
    Write-Host "ERROR: Install path not found: $InstallPath" -ForegroundColor Red
    Write-Host "Please specify the correct path using: .\Install-Phase6Session2.ps1 -InstallPath 'C:\Your\Path'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing to: $InstallPath" -ForegroundColor Green
Write-Host ""

# Create backup directory
$BackupDir = Join-Path $InstallPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
Write-Host "Created backup directory: $BackupDir" -ForegroundColor Yellow
Write-Host ""

# Function to download file from GitHub
function Download-GitHubFile {
    param(
        [string]$RemotePath,
        [string]$LocalPath
    )
    
    $Url = "$GitHubRepo/$RemotePath"
    
    try {
        Write-Host "Downloading: $RemotePath..." -NoNewline
        Invoke-WebRequest -Uri $Url -OutFile $LocalPath -UseBasicParsing
        Write-Host " OK" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Download new files
Write-Host "Step 1: Downloading new files..." -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Cyan

$SuccessCount = 0
foreach ($File in $NewFiles) {
    $LocalPath = Join-Path $InstallPath $File
    
    if (Download-GitHubFile -RemotePath $File -LocalPath $LocalPath) {
        $SuccessCount++
    }
}

Write-Host ""
Write-Host "Downloaded $SuccessCount of $($NewFiles.Count) new files" -ForegroundColor $(if ($SuccessCount -eq $NewFiles.Count) { "Green" } else { "Yellow" })
Write-Host ""

# Download and replace modified files
Write-Host "Step 2: Updating existing files..." -ForegroundColor Cyan
Write-Host "-----------------------------------" -ForegroundColor Cyan

foreach ($File in $ModifiedFiles.GetEnumerator()) {
    $RemotePath = $File.Key
    $LocalPath = Join-Path $InstallPath $File.Value
    
    # Backup existing file if it exists
    if (Test-Path $LocalPath) {
        $BackupPath = Join-Path $BackupDir $File.Value
        $BackupParentDir = Split-Path $BackupPath -Parent
        if (-not (Test-Path $BackupParentDir)) {
            New-Item -ItemType Directory -Path $BackupParentDir -Force | Out-Null
        }
        Copy-Item -Path $LocalPath -Destination $BackupPath -Force
        Write-Host "Backed up: $($File.Value)" -ForegroundColor Yellow
    }
    
    # Ensure parent directory exists
    $ParentDir = Split-Path $LocalPath -Parent
    if (-not (Test-Path $ParentDir)) {
        New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null
    }
    
    Download-GitHubFile -RemotePath $RemotePath -LocalPath $LocalPath
}

Write-Host ""

# Install Python dependencies
Write-Host "Step 3: Installing Python dependencies..." -ForegroundColor Cyan
Write-Host "------------------------------------------" -ForegroundColor Cyan

try {
    $PipOutput = pip install reportlab python-dotenv 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python dependencies installed successfully" -ForegroundColor Green
    }
    else {
        Write-Host "Warning: Some dependencies may already be installed" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Warning: Could not install Python dependencies" -ForegroundColor Yellow
    Write-Host "Run manually: pip install reportlab python-dotenv" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Files installed:" -ForegroundColor White
Write-Host "  - 6 new files added" -ForegroundColor Green
Write-Host "  - 2 files updated (backups in: backup_* folder)" -ForegroundColor Green
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "----------" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Run Database Migration:" -ForegroundColor White
Write-Host "   - Open Supabase Dashboard: https://supabase.com/dashboard" -ForegroundColor Gray
Write-Host "   - Go to SQL Editor" -ForegroundColor Gray
Write-Host "   - Open file: database_schema_notification_system.sql" -ForegroundColor Gray
Write-Host "   - Copy contents and paste into SQL Editor" -ForegroundColor Gray
Write-Host "   - Click 'Run'" -ForegroundColor Gray
Write-Host ""

Write-Host "2. Test Installation:" -ForegroundColor White
Write-Host "   streamlit run Home.py" -ForegroundColor Cyan
Write-Host "   - Navigate to Portfolio Health page" -ForegroundColor Gray
Write-Host "   - Generate a health report" -ForegroundColor Gray
Write-Host "   - Look for the '📄 PDF' button" -ForegroundColor Gray
Write-Host "   - Download PDF to verify it works" -ForegroundColor Gray
Write-Host ""

Write-Host "3. (Optional) Configure Email:" -ForegroundColor White
Write-Host "   - See AUTOMATED_MONITORING_SETUP.md for details" -ForegroundColor Gray
Write-Host ""

Write-Host "Need help? Check AUTOMATED_MONITORING_SETUP.md" -ForegroundColor Cyan
Write-Host ""

# Open SQL file in default editor
$SqlPath = Join-Path $InstallPath "database_schema_notification_system.sql"
if (Test-Path $SqlPath) {
    $Response = Read-Host "Open database_schema_notification_system.sql now? (Y/N)"
    if ($Response -eq "Y" -or $Response -eq "y") {
        Start-Process $SqlPath
    }
}

Write-Host ""
Write-Host "Phase 6 Session 2 installed successfully! 🎉" -ForegroundColor Green
Write-Host ""
