$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/add-asc842-reports-2408"

$files = @(
    @{ Url = "$base/asc842_report.py"; Out = "asc842_report.py" },
    @{ Url = "$base/email_delivery.py"; Out = "email_delivery.py" },
    @{ Url = "$base/pages/5_%F0%9F%93%88_ASC842_Dashboard.py"; Out = "pages/5_📈_ASC842_Dashboard.py" }
)

foreach ($file in $files) {
    Write-Host "Downloading $($file.Out)"
    Invoke-WebRequest -Uri $file.Url -OutFile $file.Out
}

Write-Host "Restart Streamlit, then open ASC 842 → Generate Reports."
