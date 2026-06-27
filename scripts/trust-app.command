#!/bin/bash
# Move to the script's directory
cd "$(dirname "$0")"

echo "================================================="
echo "  MM-Tools macOS App Trust Utility"
echo "================================================="
echo ""
echo "This script strips the macOS Gatekeeper quarantine flag"
echo "from MM-Tools.app so it can launch cleanly."
echo ""

TARGET_APP="MM-Tools.app"

if [ -d "$TARGET_APP" ]; then
    echo "Found app in local directory: $TARGET_APP"
    xattr -rd com.apple.quarantine "$TARGET_APP"
    echo "Successfully updated permissions! You can now open MM-Tools.app."
elif [ -d "/Applications/MM-Tools.app" ]; then
    echo "Found app in Applications directory: /Applications/MM-Tools.app"
    xattr -rd com.apple.quarantine "/Applications/MM-Tools.app"
    echo "Successfully updated permissions! You can now open the app from Applications."
else
    echo "Could not find MM-Tools.app in the current folder or /Applications."
    echo "Please place this script in the same folder as the app and run again."
fi

echo ""
read -p "Press Enter to exit..."
