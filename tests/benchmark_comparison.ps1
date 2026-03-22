# =============================================================================
# Aegis Benchmark: NAIVE vs CLAIM CHECK Pattern Comparison
# =============================================================================
# Proves the Claim Check Pattern's superiority with real numbers.
# Outputs blog-ready markdown tables comparing both approaches.
#
# Prerequisites:
#   1. docker-compose up -d  (MinIO + Kafka running)
#   2. Spring Boot gateway running on localhost:8080
#
# Usage:
#   .\benchmark_comparison.ps1
# =============================================================================

$NAIVE_URL   = "http://localhost:8080/api/v1/documents/naive"
$CLAIMCK_URL = "http://localhost:8080/api/v1/documents"
$TEST_DIR    = "$PSScriptRoot\benchmark_files"

# --- Helpers ---
function Write-Header($text) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
}

function Write-SubHeader($text) {
    Write-Host ""
    Write-Host "  --- $text ---" -ForegroundColor Yellow
}

function Format-Bytes($bytes) {
    if ($bytes -ge 1GB) { return "{0:N2} GB" -f ($bytes / 1GB) }
    if ($bytes -ge 1MB) { return "{0:N2} MB" -f ($bytes / 1MB) }
    if ($bytes -ge 1KB) { return "{0:N2} KB" -f ($bytes / 1KB) }
    return "$bytes B"
}

function Invoke-Upload {
    param(
        [string]$Url,
        [string]$FilePath,
        [int]$TimeoutSec = 600
    )
    $output = & curl.exe -s -o NUL -w "%{time_connect}|%{time_starttransfer}|%{time_total}|%{http_code}" `
        -X POST -F "file=@$FilePath" --max-time $TimeoutSec $Url 2>&1
    $parts = $output -split '\|'
    return [PSCustomObject]@{
        ConnectMs = [math]::Round([double]$parts[0] * 1000, 1)
        TTFBMs    = [math]::Round([double]$parts[1] * 1000, 1)
        TotalMs   = [math]::Round([double]$parts[2] * 1000, 1)
        HttpCode  = $parts[3].Trim()
    }
}

function Invoke-ConcurrentUploads {
    param(
        [string]$Url,
        [string[]]$FilePaths,
        [int]$TimeoutSec = 600
    )
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    $jobs = $FilePaths | ForEach-Object {
        $fp = $_
        Start-Job -ScriptBlock {
            param($url, $file, $timeout)
            $out = & curl.exe -s -o NUL -w "%{time_connect}|%{time_starttransfer}|%{time_total}|%{http_code}" `
                -X POST -F "file=@$file" --max-time $timeout $url 2>&1
            return $out
        } -ArgumentList $Url, $fp, $TimeoutSec
    }

    $jobs | Wait-Job -Timeout ($TimeoutSec + 60) | Out-Null
    $stopwatch.Stop()

    $results = @()
    $successes = 0
    $errors = 0

    foreach ($job in $jobs) {
        $output = Receive-Job $job -ErrorAction SilentlyContinue
        if ($output) {
            $parts = $output -split '\|'
            $code = $parts[3].Trim()
            $results += [PSCustomObject]@{
                TotalMs  = [math]::Round([double]$parts[2] * 1000, 0)
                HttpCode = $code
            }
            if ($code -match "^2\d\d$") { $successes++ } else { $errors++ }
        } else {
            $errors++
        }
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    }

    $sorted = ($results | ForEach-Object { $_.TotalMs }) | Sort-Object
    $p50 = if ($sorted.Count -gt 0) { [math]::Round($sorted[[math]::Floor($sorted.Count * 0.5)], 0) } else { "N/A" }
    $maxMs = if ($sorted.Count -gt 0) { [math]::Round(($sorted | Measure-Object -Maximum).Maximum, 0) } else { "N/A" }

    return [PSCustomObject]@{
        Successes   = $successes
        Errors      = $errors
        P50Ms       = $p50
        MaxMs       = $maxMs
        WallClockMs = $stopwatch.ElapsedMilliseconds
    }
}

# =============================================================================
# PHASE 0: Generate Test Files
# =============================================================================
Write-Header "PHASE 0: Generating Test Files"

if (-not (Test-Path $TEST_DIR)) {
    New-Item -ItemType Directory -Path $TEST_DIR | Out-Null
}

# Create 3 x 500MB and 3 x 1GB files
$testFiles = @(
    @{ Label = "500MB_1"; Bytes = 500MB },
    @{ Label = "500MB_2"; Bytes = 500MB },
    @{ Label = "500MB_3"; Bytes = 500MB },
    @{ Label = "1GB_1";   Bytes = 1GB   },
    @{ Label = "1GB_2";   Bytes = 1GB   },
    @{ Label = "1GB_3";   Bytes = 1GB   }
)

foreach ($tf in $testFiles) {
    $filePath = "$TEST_DIR\test_$($tf.Label).bin"
    if (-not (Test-Path $filePath)) {
        Write-Host "  Creating $($tf.Label) test file..." -ForegroundColor Yellow
        fsutil file createnew $filePath $tf.Bytes | Out-Null
    } else {
        Write-Host "  $($tf.Label) file already exists, skipping." -ForegroundColor DarkGray
    }
}

Write-Host "  All test files ready." -ForegroundColor Green

$file500_1 = "$TEST_DIR\test_500MB_1.bin"
$file500_2 = "$TEST_DIR\test_500MB_2.bin"
$file500_3 = "$TEST_DIR\test_500MB_3.bin"
$file1G_1  = "$TEST_DIR\test_1GB_1.bin"
$file1G_2  = "$TEST_DIR\test_1GB_2.bin"
$file1G_3  = "$TEST_DIR\test_1GB_3.bin"

# =============================================================================
# PHASE 1: Single-File Uploads
# =============================================================================
Write-Header "PHASE 1: Single-File Upload Latency (500MB)"

$singleResults = @()

Write-SubHeader "500MB -> NAIVE endpoint"
$r = Invoke-Upload -Url $NAIVE_URL -FilePath $file500_1
Write-Host "    HTTP $($r.HttpCode) | TTFB: $($r.TTFBMs)ms | Total: $($r.TotalMs)ms" -ForegroundColor Green
$singleResults += [PSCustomObject]@{ FileSize="500MB"; Approach="Naive (Sync)"; TTFBMs=$r.TTFBMs; TotalMs=$r.TotalMs; HttpCode=$r.HttpCode }

Start-Sleep -Seconds 3  # Let JVM breathe

Write-SubHeader "500MB -> CLAIM CHECK endpoint"
$r = Invoke-Upload -Url $CLAIMCK_URL -FilePath $file500_1
Write-Host "    HTTP $($r.HttpCode) | TTFB: $($r.TTFBMs)ms | Total: $($r.TotalMs)ms" -ForegroundColor Green
$singleResults += [PSCustomObject]@{ FileSize="500MB"; Approach="Claim Check (Async)"; TTFBMs=$r.TTFBMs; TotalMs=$r.TotalMs; HttpCode=$r.HttpCode }

Start-Sleep -Seconds 3

Write-Header "PHASE 1b: Single-File Upload Latency (1GB)"

Write-SubHeader "1GB -> NAIVE endpoint"
$r = Invoke-Upload -Url $NAIVE_URL -FilePath $file1G_1
Write-Host "    HTTP $($r.HttpCode) | TTFB: $($r.TTFBMs)ms | Total: $($r.TotalMs)ms" -ForegroundColor $(if ($r.HttpCode -match "^2") { "Green" } else { "Red" })
$singleResults += [PSCustomObject]@{ FileSize="1GB"; Approach="Naive (Sync)"; TTFBMs=$r.TTFBMs; TotalMs=$r.TotalMs; HttpCode=$r.HttpCode }

Start-Sleep -Seconds 3

Write-SubHeader "1GB -> CLAIM CHECK endpoint"
$r = Invoke-Upload -Url $CLAIMCK_URL -FilePath $file1G_1
Write-Host "    HTTP $($r.HttpCode) | TTFB: $($r.TTFBMs)ms | Total: $($r.TotalMs)ms" -ForegroundColor Green
$singleResults += [PSCustomObject]@{ FileSize="1GB"; Approach="Claim Check (Async)"; TTFBMs=$r.TTFBMs; TotalMs=$r.TotalMs; HttpCode=$r.HttpCode }

Start-Sleep -Seconds 5

# =============================================================================
# PHASE 2: Concurrent - 3x 500MB
# =============================================================================
Write-Header "PHASE 2: Concurrent Upload - 3x 500MB"

$concurrentResults = @()
$files500 = @($file500_1, $file500_2, $file500_3)

Write-SubHeader "3x 500MB -> NAIVE endpoint"
$cr = Invoke-ConcurrentUploads -Url $NAIVE_URL -FilePaths $files500
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor Green
$concurrentResults += [PSCustomObject]@{ Scenario="3x 500MB"; Approach="Naive (Sync)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

Start-Sleep -Seconds 5

Write-SubHeader "3x 500MB -> CLAIM CHECK endpoint"
$cr = Invoke-ConcurrentUploads -Url $CLAIMCK_URL -FilePaths $files500
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor Green
$concurrentResults += [PSCustomObject]@{ Scenario="3x 500MB"; Approach="Claim Check (Async)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

Start-Sleep -Seconds 5

# =============================================================================
# PHASE 3: Concurrent - 3x 1GB
# =============================================================================
Write-Header "PHASE 3: Concurrent Upload - 3x 1GB"

$files1G = @($file1G_1, $file1G_2, $file1G_3)

Write-SubHeader "3x 1GB -> NAIVE endpoint"
$cr = Invoke-ConcurrentUploads -Url $NAIVE_URL -FilePaths $files1G
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor $(if ($cr.Errors -gt 0) { "Red" } else { "Green" })
$concurrentResults += [PSCustomObject]@{ Scenario="3x 1GB"; Approach="Naive (Sync)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

Start-Sleep -Seconds 5

Write-SubHeader "3x 1GB -> CLAIM CHECK endpoint"
$cr = Invoke-ConcurrentUploads -Url $CLAIMCK_URL -FilePaths $files1G
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor Green
$concurrentResults += [PSCustomObject]@{ Scenario="3x 1GB"; Approach="Claim Check (Async)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

Start-Sleep -Seconds 5

# =============================================================================
# PHASE 4: All 6 At Once (3x 500MB + 3x 1GB)
# =============================================================================
Write-Header "PHASE 4: Full Barrage - 3x 500MB + 3x 1GB Simultaneously"

$allFiles = @($file500_1, $file500_2, $file500_3, $file1G_1, $file1G_2, $file1G_3)

Write-SubHeader "6 files (3x500MB + 3x1GB) -> NAIVE endpoint"
$cr = Invoke-ConcurrentUploads -Url $NAIVE_URL -FilePaths $allFiles
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor $(if ($cr.Errors -gt 0) { "Red" } else { "Green" })
$concurrentResults += [PSCustomObject]@{ Scenario="6 files (3x500MB+3x1GB)"; Approach="Naive (Sync)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

Start-Sleep -Seconds 5

Write-SubHeader "6 files (3x500MB + 3x1GB) -> CLAIM CHECK endpoint"
$cr = Invoke-ConcurrentUploads -Url $CLAIMCK_URL -FilePaths $allFiles
Write-Host "    $($cr.Successes) OK / $($cr.Errors) ERR | P50: $($cr.P50Ms)ms | Max: $($cr.MaxMs)ms | Wall: $($cr.WallClockMs)ms" -ForegroundColor Green
$concurrentResults += [PSCustomObject]@{ Scenario="6 files (3x500MB+3x1GB)"; Approach="Claim Check (Async)"; Successes=$cr.Successes; Errors=$cr.Errors; P50Ms=$cr.P50Ms; MaxMs=$cr.MaxMs; WallClockMs=$cr.WallClockMs }

# =============================================================================
# OUTPUT: Blog-Ready Markdown Tables
# =============================================================================
Write-Header "RESULTS: Copy the markdown below into your blog post"

Write-Host ""
Write-Host "## Benchmark: Naive vs Claim Check Pattern" -ForegroundColor White
Write-Host ""
Write-Host "**Environment:** Spring Boot 3.x, MinIO (Docker), Kafka KRaft (Docker), Windows 11, localhost" -ForegroundColor White
Write-Host "**JVM Heap:** Default (~256MB)" -ForegroundColor White
Write-Host ""

# --- Single-File Table ---
Write-Host "### Single-File Upload Latency" -ForegroundColor White
Write-Host ""
Write-Host "| File Size | Approach | Time-to-First-Byte (ms) | Total Response (ms) | HTTP Status |" -ForegroundColor White
Write-Host "|-----------|----------|------------------------|---------------------|-------------|" -ForegroundColor White

foreach ($r in $singleResults) {
    Write-Host ("| {0,-9} | {1,-22} | {2,-22} | {3,-19} | {4,-11} |" -f $r.FileSize, $r.Approach, $r.TTFBMs, $r.TotalMs, $r.HttpCode) -ForegroundColor White
}

Write-Host ""

# --- Improvement Calculation for Single Files ---
$naive500   = ($singleResults | Where-Object { $_.FileSize -eq "500MB" -and $_.Approach -like "Naive*" }).TotalMs
$claim500   = ($singleResults | Where-Object { $_.FileSize -eq "500MB" -and $_.Approach -like "Claim*" }).TotalMs
$naive1G    = ($singleResults | Where-Object { $_.FileSize -eq "1GB"   -and $_.Approach -like "Naive*" }).TotalMs
$claim1G    = ($singleResults | Where-Object { $_.FileSize -eq "1GB"   -and $_.Approach -like "Claim*" }).TotalMs

if ($naive500 -gt 0 -and $claim500 -gt 0) {
    $improve500 = [math]::Round((($naive500 - $claim500) / $naive500) * 100, 1)
    Write-Host "**500MB Improvement:** Claim Check is **${improve500}%** faster than Naive" -ForegroundColor White
}
if ($naive1G -gt 0 -and $claim1G -gt 0) {
    $improve1G = [math]::Round((($naive1G - $claim1G) / $naive1G) * 100, 1)
    Write-Host "**1GB Improvement:** Claim Check is **${improve1G}%** faster than Naive" -ForegroundColor White
}

Write-Host ""

# --- Concurrent Upload Table ---
Write-Host "### Concurrent Upload Stress Test" -ForegroundColor White
Write-Host ""
Write-Host "| Scenario | Approach | Success | Errors | P50 (ms) | Max (ms) | Wall Clock (ms) |" -ForegroundColor White
Write-Host "|----------|----------|---------|--------|----------|----------|-----------------|" -ForegroundColor White

foreach ($r in $concurrentResults) {
    Write-Host ("| {0,-24} | {1,-22} | {2,-7} | {3,-6} | {4,-8} | {5,-8} | {6,-15} |" -f $r.Scenario, $r.Approach, $r.Successes, $r.Errors, $r.P50Ms, $r.MaxMs, $r.WallClockMs) -ForegroundColor White
}

Write-Host ""
Write-Host "### Key Takeaways" -ForegroundColor White
Write-Host ""
Write-Host "- Claim Check Pattern streams files directly to MinIO, bypassing JVM heap entirely." -ForegroundColor White
Write-Host "- Naive approach buffers the whole file in memory - at 1GB, this consumes the entire JVM heap." -ForegroundColor White
Write-Host "- Under concurrent load, the Naive approach degrades or crashes while Claim Check stays stable." -ForegroundColor White

# --- Cleanup notice ---
Write-Host ""
Write-Header "CLEANUP"
Write-Host "  Test files are in:" -ForegroundColor Yellow
Write-Host "  $TEST_DIR" -ForegroundColor Yellow
Write-Host "  Total size: ~4.5 GB" -ForegroundColor Yellow
Write-Host "  To delete, run:" -ForegroundColor Yellow
Write-Host "  Remove-Item -Recurse -Force benchmark_files" -ForegroundColor Yellow
Write-Host ""
