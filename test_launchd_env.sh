#!/bin/bash
# Test script to simulate launchd environment
# This runs the backup script with a minimal PATH (like launchd)

echo "Testing script in launchd-like environment (minimal PATH)..."
echo ""

# Simulate launchd's minimal PATH
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

# Run the validation
python3 vbox_backup.py --validate

echo ""
echo "If validation passed above, the script should work with launchd."
echo "If it failed, check the error message and update your config.json"
