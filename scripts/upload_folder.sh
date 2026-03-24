#!/bin/bash

# Check if folder path is provided
if [ -z "$1" ]; then
    echo -e "\033[31mError: Please provide a folder path.\033[0m"
    echo "Usage: ./upload_folder.sh <folder_path>"
    exit 1
fi

FOLDER_PATH="$1"

# Check if folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo -e "\033[31mError: Directory '$FOLDER_PATH' does not exist.\033[0m"
    exit 1
fi

echo -e "\033[36mScanning $FOLDER_PATH for documents and code...\033[0m"

# Find all files, ignoring hidden directories like .git and .venv
find "$FOLDER_PATH" -type f -not -path "*/\.*" -not -path "*/venv/*" | while read -r FILE; do
    # Extract the relative path to preserve directory context in the RAG engine
    CLEAN_BASE=$(echo "$FOLDER_PATH" | sed 's:/*$::')
    REL_PATH="${FILE#$CLEAN_BASE/}"
    
    echo -n "Uploading: $REL_PATH... "
    
    # Fire the curl command, explicitly overriding the filename to include the directory path
    RESPONSE=$(curl -s -X POST -F "file=@$FILE;filename=$REL_PATH" http://localhost:8080/api/v1/documents)
    
    if echo "$RESPONSE" | grep -q '"status":"accepted"'; then
        echo -e "\033[32m[SUCCESS]\033[0m"
    else
        echo -e "\033[31m[FAILED]\033[0m"
        echo -e "\033[90mResponse: $RESPONSE\033[0m"
    fi
done

echo -e "\n\033[36mBatch ingestion complete! The Python AI worker is now processing the queue in the background.\033[0m"