param (
    [Parameter(Mandatory=$true)]
    [string]$FolderPath
)

if (-Not (Test-Path $FolderPath)) {
    Write-Host "Error: Folder '$FolderPath' does not exist." -ForegroundColor Red
    exit 1
}

# Get all PDF and TXT files in the folder
$files = Get-ChildItem -Path $FolderPath -Include *.pdf, *.txt -Recurse

if ($files.Count -eq 0) {
    Write-Host "No PDF or TXT files found in $FolderPath" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($files.Count) files. Beginning batch ingestion to Project Aegis..." -ForegroundColor Cyan

foreach ($file in $files) {
    Write-Host "Uploading: $($file.Name)..." -NoNewline
    
    # Fire the curl command to the Spring Boot Gateway
    $response = curl.exe -s -X POST -F "file=@$($file.FullName)" http://localhost:8080/api/v1/documents
    
    if ($response -match '"status":"accepted"') {
        Write-Host " [SUCCESS]" -ForegroundColor Green
    } else {
        Write-Host " [FAILED]" -ForegroundColor Red
        Write-Host "Response: $response" -ForegroundColor DarkGray
    }
}

Write-Host "`nBatch ingestion complete! The Python AI worker is now processing the queue in the background." -ForegroundColor Cyan