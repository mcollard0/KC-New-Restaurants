#!/bin/bash
"""
KC Restaurants Crash-Aware Runner

Wrapper script that:
- Detects and recovers from segmentation faults (exit code 139)  
- Enables core dumps for debugging
- Provides retry logic with backoff
- Logs crashes and recovery attempts
- Sets up proper environment for debugging
"""

set -euo pipefail;

# Configuration
readonly SCRIPT_NAME="KC New Restaurants.py";
readonly LOG_FILE="${HOME}/logs/kc_restaurants/crash_recovery_$(date +%Y%m%d_%H%M%S).log";
readonly MAX_RETRIES=3;
readonly RETRY_DELAY=30;  # seconds
readonly CORE_DUMP_DIR="${HOME}/core_dumps";

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")";
mkdir -p "$CORE_DUMP_DIR";

# Set up crash diagnostics environment
export PYTHONFAULTHANDLER=1;
export PYTHONUNBUFFERED=1;
export MALLOC_CHECK_=2;  # Enable glibc malloc debugging
ulimit -c unlimited;     # Enable core dumps

# Logging function
log() {
    local level="$1";
    shift;
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE";
}

# Function to analyze crash
analyze_crash() {
    local exit_code="$1";
    local attempt="$2";
    
    log "ERROR" "🚨 CRASH DETECTED 🚨";
    log "ERROR" "Exit Code: $exit_code";
    log "ERROR" "Attempt: $attempt/$MAX_RETRIES";
    log "ERROR" "Python Version: $(python3 --version 2>&1)";
    log "ERROR" "Timestamp: $(date --iso-8601=seconds)";
    
    # Check for specific crash types
    case "$exit_code" in
        139)
            log "ERROR" "SIGSEGV (Segmentation Fault) - Memory access violation";
            log "ERROR" "This is the PyObject_getItem() crash we're tracking";
            ;;
        135)
            log "ERROR" "SIGBUS (Bus Error) - Hardware-level memory access error";
            ;;
        136)
            log "ERROR" "SIGFPE (Floating Point Exception)";
            ;;
        134)
            log "ERROR" "SIGABRT (Abort) - Program called abort()";
            ;;
        137)
            log "ERROR" "SIGKILL (Kill signal) - Process was forcibly terminated";
            ;;
        *)
            log "ERROR" "Unknown crash type with exit code $exit_code";
            ;;
    esac;
    
    # Look for core dump
    local core_file=$(find "$CORE_DUMP_DIR" -name "core*" -newer "$LOG_FILE" 2>/dev/null | head -1);
    if [[ -n "$core_file" ]]; then
        log "INFO" "Core dump found: $core_file";
        
        # Analyze with gdb if available
        if command -v gdb >/dev/null 2>&1; then
            log "INFO" "Analyzing core dump with GDB...";
            echo "=== GDB BACKTRACE ===" >> "$LOG_FILE";
            timeout 30 gdb -batch -ex "bt full" -ex "quit" python3 "$core_file" >> "$LOG_FILE" 2>&1 || {
                log "WARN" "GDB analysis failed or timed out";
            };
            echo "=== END GDB BACKTRACE ===" >> "$LOG_FILE";
        else
            log "WARN" "GDB not available for core dump analysis";
        fi;
    else
        log "WARN" "No core dump found - may need to check ulimit settings";
    fi;
    
    # Memory and system info
    log "INFO" "System memory info:";
    free -h >> "$LOG_FILE" 2>&1 || true;
    
    log "INFO" "System load:";
    uptime >> "$LOG_FILE" 2>&1 || true;
    
    log "INFO" "Disk space:";
    df -h "$(pwd)" >> "$LOG_FILE" 2>&1 || true;
}

# Function to send crash notification
send_crash_notification() {
    local exit_code="$1";
    local attempt="$2";
    
    # Try to send email notification if configured
    if [[ -n "${CRASH_EMAIL:-}" ]] && command -v mail >/dev/null 2>&1; then
        {
            echo "KC New Restaurants crashed with exit code $exit_code";
            echo "Attempt: $attempt/$MAX_RETRIES";
            echo "Timestamp: $(date --iso-8601=seconds)";
            echo "Log file: $LOG_FILE";
            echo "";
            echo "Last 50 lines of log:";
            tail -50 "$LOG_FILE" 2>/dev/null || echo "Could not read log file";
        } | mail -s "KC Restaurants Crash Alert" "$CRASH_EMAIL" || {
            log "WARN" "Failed to send email notification";
        };
    fi;
    
    # Try to send Slack notification if configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local slack_message="{
            \"text\": \"🚨 KC New Restaurants crashed\",
            \"attachments\": [{
                \"color\": \"danger\",
                \"fields\": [
                    {\"title\": \"Exit Code\", \"value\": \"$exit_code\", \"short\": true},
                    {\"title\": \"Attempt\", \"value\": \"$attempt/$MAX_RETRIES\", \"short\": true},
                    {\"title\": \"Timestamp\", \"value\": \"$(date --iso-8601=seconds)\", \"short\": true},
                    {\"title\": \"Log File\", \"value\": \"$LOG_FILE\", \"short\": true}
                ]
            }]
        }";
        
        curl -X POST -H 'Content-type: application/json' \
             --data "$slack_message" \
             "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || {
            log "WARN" "Failed to send Slack notification";
        };
    fi;
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites...";
    
    # Check if script exists
    if [[ ! -f "$SCRIPT_NAME" ]]; then
        log "ERROR" "Script not found: $SCRIPT_NAME";
        exit 1;
    fi;
    
    # Check Python version
    local python_version=$(python3 --version 2>&1);
    log "INFO" "Python version: $python_version";
    
    # Warn about Python 3.13 issues
    if [[ "$python_version" == *"3.13"* ]]; then
        log "WARN" "Running Python 3.13 - known to have PyObject_getItem() SIGSEGV issues";
    fi;
    
    # Check available memory
    local available_memory=$(free -m | awk '/^Mem:/{print $7}');
    if [[ "$available_memory" -lt 100 ]]; then
        log "WARN" "Low memory available: ${available_memory}MB";
    fi;
    
    log "INFO" "Prerequisites check complete";
}

# Main execution function
run_with_recovery() {
    local attempt=1;
    
    log "INFO" "Starting KC New Restaurants with crash recovery";
    log "INFO" "Command: python3 '$SCRIPT_NAME' $*";
    log "INFO" "Max retries: $MAX_RETRIES";
    log "INFO" "Retry delay: ${RETRY_DELAY}s";
    
    while [[ $attempt -le $MAX_RETRIES ]]; do
        log "INFO" "=== ATTEMPT $attempt/$MAX_RETRIES ===";
        
        # Clear any old context
        unset CRASH_CONTEXT;
        export CRASH_CONTEXT="attempt_${attempt}";
        
        # Run the script
        set +e;  # Don't exit on error
        python3 "$SCRIPT_NAME" "$@";
        local exit_code=$?;
        set -e;
        
        # Check exit code
        case "$exit_code" in
            0)
                log "INFO" "✅ Script completed successfully";
                return 0;
                ;;
            139|135|136|134)
                # Crash detected
                analyze_crash "$exit_code" "$attempt";
                send_crash_notification "$exit_code" "$attempt";
                
                if [[ $attempt -lt $MAX_RETRIES ]]; then
                    log "INFO" "💤 Waiting ${RETRY_DELAY}s before retry...";
                    sleep "$RETRY_DELAY";
                    ((attempt++));
                    log "INFO" "🔄 Retrying...";
                else
                    log "ERROR" "❌ Max retries exceeded - giving up";
                    return "$exit_code";
                fi;
                ;;
            *)
                # Other error
                log "ERROR" "Script failed with exit code: $exit_code";
                return "$exit_code";
                ;;
        esac;
    done;
    
    log "ERROR" "Unexpected end of retry loop";
    return 1;
}

# Script entry point
main() {
    log "INFO" "KC Restaurants Crash-Aware Runner starting";
    log "INFO" "Script: $SCRIPT_NAME";
    log "INFO" "Arguments: $*";
    log "INFO" "Working directory: $(pwd)";
    log "INFO" "User: $(whoami)";
    log "INFO" "PID: $$";
    
    # Set up signal handlers
    trap 'log "INFO" "Received SIGTERM - shutting down gracefully"; exit 143' TERM;
    trap 'log "INFO" "Received SIGINT - shutting down gracefully"; exit 130' INT;
    
    check_prerequisites;
    
    # Run with crash recovery
    run_with_recovery "$@";
    local final_exit_code=$?;
    
    log "INFO" "KC Restaurants Crash-Aware Runner finished with exit code: $final_exit_code";
    return "$final_exit_code";
}

# Run main function with all arguments
main "$@";