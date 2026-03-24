param (
    [Parameter(Mandatory=$true)]
    [string]$FolderPath
)

if (-Not (Test-Path $FolderPath)) {
    Write-Host "Error: Folder '$FolderPath' does not exist." -ForegroundColor Red
    exit 1
}

Write-Host "Aegis Enterprise File Watcher Started." -ForegroundColor Cyan
Write-Host "Monitoring '$FolderPath' for new files. Press Ctrl+C to exit." -ForegroundColor DarkGray

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $FolderPath
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$action = {
    $path = $Event.SourceEventArgs.FullPath
    $name = $Event.SourceEventArgs.Name
    $changeType = $Event.SourceEventArgs.ChangeType

    # Ignore temp files or hidden files
    if ($name -match '^\.' -or $name -match '~') { return }

    Write-Host "`n[NEW FILE DETECTED] $name" -ForegroundColor Yellow
    Write-Host "Streaming to Aegis Gateway..." -NoNewline

    # Convert to relative path
    $relPath = $path.Substring($FolderPath.Length).TrimStart('\', '/')
    $relPath = $relPath -replace '\\', '/'

    try {
        $response = curl.exe -s -X POST -F "file=@$path;filename=$relPath" http://localhost:8080/api/v1/documents
        
        if ($response -match '"status":"accepted"') {
            Write-Host " [SUCCESS]" -ForegroundColor Green
        } else {
            Write-Host " [FAILED]" -ForegroundColor Red
            Write-Host "Response: $response" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host " [ERROR] Gateway Offline" -ForegroundColor Red
    }
}

# Register the event
$createdEvent = Register-ObjectEvent $watcher "Created" -Action $action

# Keep the script running
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Unregister-Event -SourceIdentifier $createdEvent.Name
    $watcher.Dispose()
    Write-Host "`nWatcher stopped." -ForegroundColor Cyan
}