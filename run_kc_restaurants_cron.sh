#!/bin/bash
#
# KC New Restaurants Cron Wrapper Script
# 
# This script provides enhanced logging and error handling for cron execution
#

# Set script directory and log paths
SCRIPT_DIR="/media/michael/FASTESTARCHIVE/Archive/Programming/Python/KC New Restaurants"
LOG_DIR="$SCRIPT_DIR/log"
SCRIPT_FILE="KC New Restaurants.py"

# Create date-stamped log file
DATE_STAMP=$(date +%F)
LOG_FILE="$LOG_DIR/kc_cron_${DATE_STAMP}.log"

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log_with_timestamp "=== KC NEW RESTAURANTS CRON JOB STARTED ==="
log_with_timestamp "Script directory: $SCRIPT_DIR"
log_with_timestamp "Log file: $LOG_FILE"
log_with_timestamp "Python version: $(python3 --version 2>&1)"
log_with_timestamp "Working directory: $(pwd)"

# Change to script directory
if cd "$SCRIPT_DIR"; then
    log_with_timestamp "✅ Successfully changed to script directory"
else
    log_with_timestamp "❌ FAILED to change to script directory: $SCRIPT_DIR"
    exit 1
fi

# Verify script exists
if [ -f "$SCRIPT_FILE" ]; then
    log_with_timestamp "✅ Script file found: $SCRIPT_FILE"
else
    log_with_timestamp "❌ SCRIPT FILE NOT FOUND: $SCRIPT_FILE"
    log_with_timestamp "Available files in directory:"
    ls -la >> "$LOG_FILE" 2>&1
    exit 1
fi

# Check if log directory is writable
if [ -w "$LOG_DIR" ]; then
    log_with_timestamp "✅ Log directory is writable"
else
    log_with_timestamp "⚠️  WARNING: Log directory may not be writable"
fi

# Execute the main script
log_with_timestamp "🚀 Starting KC New Restaurants script execution..."

# Run the script and capture both stdout and stderr
if python3 "$SCRIPT_FILE" >> "$LOG_FILE" 2>&1; then
    EXIT_CODE=$?
    log_with_timestamp "✅ Script execution completed successfully (exit code: $EXIT_CODE)"
else
    EXIT_CODE=$?
    log_with_timestamp "❌ Script execution failed (exit code: $EXIT_CODE)"
fi

# Log completion
log_with_timestamp "=== KC NEW RESTAURANTS CRON JOB COMPLETED ==="
log_with_timestamp "Final exit code: $EXIT_CODE"

# Rotate logs if they get too large (keep only last 10 MB)
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo "0")
    if [ "$LOG_SIZE" -gt 10485760 ]; then # 10MB
        log_with_timestamp "📋 Log file size: ${LOG_SIZE} bytes - rotating..."
        # Keep backup of large log
        mv "$LOG_FILE" "${LOG_FILE}.large.$(date +%H%M%S)"
        log_with_timestamp "📋 Log rotated due to size limit"
    fi
fi

exit $EXIT_CODE