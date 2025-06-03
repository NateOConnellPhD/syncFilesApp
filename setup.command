#!/bin/bash

# Get the directory this script is in
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# Remove quarantine flag from the whole folder
xattr -rd com.apple.quarantine "$APP_DIR"

# Optional: open the app
open "$APP_DIR/appLauncher/appLauncher.app"
