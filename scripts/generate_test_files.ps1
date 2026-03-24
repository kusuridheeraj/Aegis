param (
    [switch]$Clean
)

$Path500MB = ".\temp_500mb.bin"
$Path1GB = ".\temp_1gb.bin"

if ($Clean) {
    Write-Host "Cleaning up test files..." -ForegroundColor Yellow
    if (Test-Path $Path500MB) { Remove-Item $Path500MB; Write-Host "Deleted $Path500MB" }
    if (Test-Path $Path1GB) { Remove-Item $Path1GB; Write-Host "Deleted $Path1GB" }
    Write-Host "Cleanup complete." -ForegroundColor Green
    exit
}

Write-Host "Generating massive test files for Aegis benchmarks..." -ForegroundColor Cyan

# 500MB = 500 * 1024 * 1024 = 524288000 bytes
if (-Not (Test-Path $Path500MB)) {
    Write-Host "Creating 500MB file..."
    fsutil file createnew $Path500MB 524288000 | Out-Null
    Write-Host "Created $Path500MB" -ForegroundColor Green
} else {
    Write-Host "$Path500MB already exists." -ForegroundColor Gray
}

# 1GB = 1024 * 1024 * 1024 = 1073741824 bytes
if (-Not (Test-Path $Path1GB)) {
    Write-Host "Creating 1GB file..."
    fsutil file createnew $Path1GB 1073741824 | Out-Null
    Write-Host "Created $Path1GB" -ForegroundColor Green
} else {
    Write-Host "$Path1GB already exists." -ForegroundColor Gray
}

Write-Host "`nTest files are ready! You can now use them in your curl commands." -ForegroundColor Cyan
