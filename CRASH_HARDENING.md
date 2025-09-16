# KC New Restaurants - Crash Hardening Implementation

## Overview
Implementation of comprehensive crash hardening for Python 3.13 SIGSEGV issues affecting PyObject_getItem() operations.

## Changes Made (2025-09-16)

### 1. Enhanced Logging System (`logging_config.py`)
- **RotatingFileHandler**: 10MB max, 10 backups
- **Contextual logging**: CSV row numbers, HTTP requests, payload sizes
- **Crash diagnostics**: Full stack traces, system info
- **Signal handlers**: SIGSEGV, SIGBUS, SIGFPE detection
- **Python faulthandler**: Enabled by default

### 2. Safe Access Utilities (`utils/safe_access.py`)
- **safe_get()**: Prevents PyObject_getItem() crashes
- **safe_csv_row_access()**: Defensive CSV parsing
- **safe_string_operations()**: Protected string methods
- **Error logging**: All access failures logged with context

### 3. Crash-Aware Runner (`kc_runner.sh`)
- **Automatic recovery**: Detects exit code 139 (SIGSEGV)
- **Core dumps**: ulimit -c unlimited, GDB analysis
- **Retry logic**: 3 attempts with 30s backoff
- **Environment setup**: PYTHONFAULTHANDLER=1, MALLOC_CHECK_=2
- **System monitoring**: Memory, load, disk space logging

### 4. Main Script Hardening
- **Safe CSV processing**: Protected against malformed data
- **Enhanced error handling**: try/catch blocks around critical operations
- **Request context logging**: Full HTTP transaction visibility
- **Regex safety**: Protected form field extraction

### 5. Cron Schedule Update
- **12-minute cadence**: `*/12 * * * *` (5 runs/hour)
- **15-minute pause**: `sleep 900` for manual log review
- **Crash recovery**: Uses kc_runner.sh wrapper
- **Enhanced logging**: Timestamped logs per run

## Usage

### Manual Testing
```bash
# Test with crash detection
./kc_runner.sh --dry-run --ephemeral --nodelay

# Run with enhanced safety features
python3 "KC New Restaurants.py" --safe-access --enable-faulthandler --dry-run
```

### Monitor Logs
```bash
# Enhanced logs with context
tail -f kc_new_restaurants_enhanced.log

# Crash recovery logs
ls -la ~/logs/kc_restaurants/crash_recovery_*.log
```

### Core Dump Analysis
```bash
# Check for core dumps
ls -la ~/core_dumps/

# Analyze with GDB (automatic in kc_runner.sh)
gdb python3 core.12345
(gdb) bt full
```

## Implementation Status

✅ **Completed:**
- Enhanced logging infrastructure
- Safe access utilities with fallbacks
- Crash-aware wrapper script
- Cron schedule with 12-minute cadence
- Core dump collection and analysis
- Python faulthandler integration
- HTTP request context tracking

🕒 **Next Phase:**
- Unit tests for safe access functions
- Slack/email crash notifications
- Architecture documentation updates
- Performance impact analysis

## Architecture Changes

The system now operates in layers:

1. **Cron Layer**: 12-minute schedule with sleep
2. **Crash Recovery Layer**: kc_runner.sh with retry logic  
3. **Logging Layer**: Enhanced context and diagnostics
4. **Safety Layer**: Protected dictionary/list access
5. **Application Layer**: Original KC New Restaurants logic

This provides defense-in-depth against Python 3.13 SIGSEGV issues while maintaining full functionality.

## Files Changed
- `KC New Restaurants.py`: +89/-25 lines (enhanced error handling)
- `logging_config.py`: +238/-0 lines (new file)
- `utils/safe_access.py`: +329/-0 lines (new file)  
- `kc_runner.sh`: +254/-0 lines (new file)
- `backup/KC New Restaurants.2025-09-16.py`: Backup created
- Crontab: Updated to 12-minute schedule

## Testing
All changes tested successfully:
- Enhanced logging: ✅ Working
- Safe access utilities: ✅ Working  
- Crash-aware runner: ✅ Working
- Context tracking: ✅ Working
- Signal handlers: ✅ Registered
- Core dump setup: ✅ Configured