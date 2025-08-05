#!/bin/bash
# Setup script for nightly error message cleanup

echo "Setting up nightly error message cleanup..."

# Make cleanup script executable
chmod +x nightly_error_cleanup.py

# Create cron job entry (runs at 2 AM daily)
CRON_ENTRY="0 2 * * * cd /home/runner/workspace && /usr/bin/python3 nightly_error_cleanup.py >> /tmp/error_cleanup.log 2>&1"

# Add to crontab (avoiding duplicates)
(crontab -l 2>/dev/null | grep -v "nightly_error_cleanup.py"; echo "$CRON_ENTRY") | crontab -

echo "✅ Nightly cleanup scheduled for 2 AM daily"
echo "✅ Logs will be written to /tmp/error_cleanup.log"
echo "✅ To test manually: python3 nightly_error_cleanup.py"
echo "✅ To view schedule: crontab -l"
echo ""
echo "Setup completed successfully!"