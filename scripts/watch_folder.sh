#!/bin/bash

if [ -z "$1" ]; then
    echo -e "\033[31mError: Please provide a folder path.\033[0m"
    echo "Usage: ./watch_folder.sh <folder_path>"
    exit 1
fi

FOLDER_PATH="$1"

if [ ! -d "$FOLDER_PATH" ]; then
    echo -e "\033[31mError: Directory '$FOLDER_PATH' does not exist.\033[0m"
    exit 1
fi

# Check if inotifywait is installed (Linux standard file watcher)
if ! command -v inotifywait &> /dev/null; then
    echo -e "\033[33mWarning: 'inotifywait' not found. Falling back to 2-second polling loop.\033[0m"
    echo "For real-time OS-level events, please install inotify-tools (e.g., sudo apt-get install inotify-tools)"
    echo -e "\033[36mMonitoring '$FOLDER_PATH' for new files...\033[0m"
    
    # Polling loop fallback
    TOUCH_FILE="/tmp/aegis_watch_$$"
    touch "$TOUCH_FILE"
    while true; do
        sleep 2
        find "$FOLDER_PATH" -type f -newer "$TOUCH_FILE" -not -path "*/\.*" | while read -r FILE; do
            CLEAN_BASE=$(echo "$FOLDER_PATH" | sed 's:/*$::')
            REL_PATH="${FILE#$CLEAN_BASE/}"
            echo -e "\n\033[33m[NEW FILE DETECTED]\033[0m $REL_PATH"
            echo -n "Streaming to Aegis Gateway... "
            RESPONSE=$(curl -s -X POST -F "file=@$FILE;filename=$REL_PATH" http://localhost:8080/api/v1/documents)
            if echo "$RESPONSE" | grep -q '"status":"accepted"'; then
                echo -e "\033[32m[SUCCESS]\033[0m"
            else
                echo -e "\033[31m[FAILED]\033[0m"
            fi
        done
        touch "$TOUCH_FILE"
    done
else
    echo -e "\033[36mAegis Enterprise File Watcher Started (inotify).\033[0m"
    echo -e "\033[90mMonitoring '$FOLDER_PATH' for new files. Press Ctrl+C to exit.\033[0m"

    inotifywait -m -r -e close_write --format '%w%f' "$FOLDER_PATH" | while read FILE; do
        # Ignore hidden files
        if [[ "$FILE" == *"/."* ]]; then continue; fi
        
        CLEAN_BASE=$(echo "$FOLDER_PATH" | sed 's:/*$::')
        REL_PATH="${FILE#$CLEAN_BASE/}"
        
        echo -e "\n\033[33m[NEW FILE DETECTED]\033[0m $REL_PATH"
        echo -n "Streaming to Aegis Gateway... "
        
        RESPONSE=$(curl -s -X POST -F "file=@$FILE;filename=$REL_PATH" http://localhost:8080/api/v1/documents)
        
        if echo "$RESPONSE" | grep -q '"status":"accepted"'; then
            echo -e "\033[32m[SUCCESS]\033[0m"
        else
            echo -e "\033[31m[FAILED]\033[0m"
            echo -e "\033[90mResponse: $RESPONSE\033[0m"
        fi
    done
fi