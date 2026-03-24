param (
    [Parameter(Mandatory=$true)]
    [string]$FolderPath
)

if (-Not (Test-Path $FolderPath)) {
    Write-Host "Error: Folder '$FolderPath' does not exist." -ForegroundColor Red
    exit 1
}

# Get all relevant files in the folder (PDFs, Logs, Code, Data)
$extensions = "*.pdf", "*.txt", "*.log", "*.md", "*.py", "*.java", "*.csv", "*.json"
$files = Get-ChildItem -Path $FolderPath -Include $extensions -Recurse

if ($files.Count -eq 0) {
    Write-Host "No valid documents found in $FolderPath" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($files.Count) files. Beginning batch ingestion to Project Aegis..." -ForegroundColor Cyan

foreach ($file in $files) {
    # Extract the relative path and convert backslashes to forward slashes
    $relPath = $file.FullName.Substring($FolderPath.Length).TrimStart('\', '/')
    $relPath = $relPath -replace '\\', '/'
    
    Write-Host "Uploading: $relPath..." -NoNewline
    
    # Fire the curl command, explicitly overriding the filename to include the directory path
    $response = curl.exe -s -X POST -F "file=@$($file.FullName);filename=$relPath" http://localhost:8080/api/v1/documents
    
    if ($response -match '"status":"accepted"') {
        Write-Host " [SUCCESS]" -ForegroundColor Green
    } else {
        Write-Host " [FAILED]" -ForegroundColor Red
        Write-Host "Response: $response" -ForegroundColor DarkGray
    }
}

Write-Host "`nBatch ingestion complete! The Python AI worker is now processing the queue in the background." -ForegroundColor Cyan