# Download the Amendment Graph upload fix into the local LeaseAI folder.
# Run from C:\Users\brody\OneDrive\Desktop\LeaseAI (or your LeaseAI directory).

Write-Host "Downloading Amendment Graph upload fix..." -ForegroundColor Cyan
$base = "https://raw.githubusercontent.com/brodyleaseai/leaseai/cursor/fix-amendment-upload-stop-2408"
New-Item -ItemType Directory -Path "pages" -Force | Out-Null

$files = @(
    @{
        Url = "$base/amendment_graph_helpers.py"
        Out = "amendment_graph_helpers.py"
        Name = "amendment_graph_helpers.py"
    },
    @{
        Url = "$base/amendment_report.py"
        Out = "amendment_report.py"
        Name = "amendment_report.py"
    },
    @{
        Url = "$base/pages/3_%F0%9F%94%97_Amendment_Graph.py"
        Out = "pages/3_🔗_Amendment_Graph.py"
        Name = "Amendment Graph page"
    }
)

foreach ($file in $files) {
    Write-Host "  $($file.Name)"
    Invoke-WebRequest -Uri $file.Url -OutFile $file.Out
}

Write-Host "Done. Restart Streamlit. Upload addenda on the Upload Amendment tab. Use Amendment Report for the client PDF." -ForegroundColor Green
