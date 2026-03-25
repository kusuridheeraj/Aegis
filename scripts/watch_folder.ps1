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
    
    # Windows curl.exe breaks completely if the file path or filename contains commas or parentheses.
    # To fix this, we copy the file to a safe temporary name, upload it, and delete the temp file.
    $safeTempPath = Join-Path $env:TEMP "aegis_temp_upload_$($Event.SourceEventArgs.ChangeType).bin"
    Copy-Item -Path $path -Destination $safeTempPath -Force
    
    # Sanitize the filename string sent to the server
    $safeFilename = $relPath -replace '[,()]', '_'

    try {
        $response = curl.exe -s -X POST -F "file=@$safeTempPath;filename=$safeFilename" http://localhost:8080/api/v1/documents
        
        if ($response -match '"status":"accepted"') {
            Write-Host " [SUCCESS]" -ForegroundColor Green
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