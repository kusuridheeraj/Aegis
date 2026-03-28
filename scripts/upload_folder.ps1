param (
    [Parameter(Mandatory=$true)]
    [string]$FolderPath
)

if (-not (Test-Path $FolderPath)) {
    Write-Host "Error: Folder '$FolderPath' not found." -ForegroundColor Red
    exit 1
}

$files = Get-ChildItem -Path $FolderPath -Include *.pdf, *.epub -Recurse

Write-Host "--- Aegis Batch Ingestion Started ---" -ForegroundColor Cyan
Write-Host "Found $($files.Count) files in '$FolderPath'" -ForegroundColor Yellow

foreach ($file in $files) {
    Write-Host "`n[UPLOADING] $($file.Name)..." -NoNewline
    
    # We use a completely safe temporary name for the DISK path to avoid curl parsing bugs
    $guid = [guid]::NewGuid().ToString()
    $safeTempPath = Join-Path $env:TEMP "aegis_tmp_$guid.bin"
    Copy-Item -Path $file.FullName -Destination $safeTempPath -Force
    
    # Aggressive sanitization for the FILENAME header sent to the server
    $safeFilename = $file.Name -replace '[^a-zA-Z0-9.]', '_'
    $safeFilename = $safeFilename -replace '__+', '_'

    try {
        $response = curl.exe -s -X POST -F "file=@$safeTempPath;filename=$safeFilename" http://localhost:8080/api/v1/documents
        
        if ($response -match '"status":"accepted"') {
            Write-Host " [ACCEPTED]" -ForegroundColor Green
        } else {
            Write-Host " [FAILED]" -ForegroundColor Red
            Write-Host "Response: $response" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host " [ERROR] Gateway Offline" -ForegroundColor Red
    } finally {
        if (Test-Path $safeTempPath) { Remove-Item $safeTempPath -Force }
    }
}

Write-Host "`n--- Batch Ingestion Complete ---" -ForegroundColor Cyan
