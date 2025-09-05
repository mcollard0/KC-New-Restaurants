# KC New Restaurants - Dry-Run Mode Documentation

## Overview

The KC New Restaurants script now includes a **dry-run mode** that allows you to safely test the script without making any actual database modifications. This is particularly useful for:

- Testing configuration changes
- Validating data processing logic
- Running against production data safely
- Debugging issues without side effects

## Usage

### Command Line Flags

The dry-run mode can be activated using any of these equivalent flags:

```bash
# Long form options
python3 "KC New Restaurants.py" --dry-run
python3 "KC New Restaurants.py" --dryrun

# Short form option
python3 "KC New Restaurants.py" -d
```

### Combining with Other Flags

Dry-run mode works with all other existing flags:

```bash
# Dry-run with ephemeral mode (no database connection)
python3 "KC New Restaurants.py" --dry-run --ephemeral --nodelay

# Dry-run with flush (would normally clear database)
python3 "KC New Restaurants.py" --dry-run --flush

# Dry-run with no delay
python3 "KC New Restaurants.py" --dry-run --nodelay
```

## What Gets Protected

When dry-run mode is enabled, the following database operations are **simulated only**:

### MongoDB Operations
- `collection.insert_one()` - New business insertions
- `collection.delete_many()` - Database flushing operations  
- `collection.drop_index()` - Index management
- `collection.create_index()` - Index creation

### Specific Functions Protected
- `flush_database()` - Database clearing operations
- `setup_mongodb()` - Index creation/deletion
- `process()` - New business record insertions

## Expected Output

### Dry-Run Banner
When dry-run mode is activated, you'll see a prominent banner:

```
======================================================================
*** DRY-RUN MODE: NO DATA WILL BE MODIFIED ***
  - All database operations will be simulated only
  - No actual INSERT, UPDATE, or DELETE operations will occur
  - This is safe for testing and validation
======================================================================
```

### Log Messages
All database operations that would normally execute will be logged with the `[DRY-RUN]` prefix:

```
[DRY-RUN] Skipping drop_index operation for business_name_1
[DRY-RUN] Skipping index creation for compound business fields
[DRY-RUN] Skipping index creation for insert_date
[DRY-RUN] Skipping insert_one for new business: Restaurant Name, Address, Business Type
[DRY-RUN] flush_database() skipped - would have deleted all documents in collection
```

## Testing the Implementation

### Quick Test
Run the included test script to verify functionality:

```bash
python3 test_dry_run.py
```

### Manual Testing
Test dry-run mode manually:

```bash
# Safe test with no external dependencies
python3 "KC New Restaurants.py" --dry-run --ephemeral --nodelay
```

### Comprehensive Test
Test against your actual database (safely):

```bash
# This will connect to your database but make no changes
python3 "KC New Restaurants.py" --dry-run --nodelay
```

## Safety Guarantees

When `--dry-run` mode is enabled:

1. **No data will be modified** - All write operations are bypassed
2. **Read operations still work** - Data can be queried and analyzed
3. **Processing logic runs** - Business logic is fully executed
4. **Statistics are accurate** - Reporting and analysis work normally
5. **Email alerts still send** - Notification system remains functional

## Integration with Existing Features

### Ephemeral Mode
- `--ephemeral`: No database connection at all
- `--dry-run`: Database connection but no writes
- Both can be used together for maximum safety

### Flush Mode
- `--flush`: Normally clears all database records
- `--dry-run --flush`: Simulates the flush operation safely

### Cron Integration
- Dry-run mode respects the `--nodelay` flag
- Safe to test cron jobs with dry-run enabled
- Production cron jobs should never use dry-run mode

## Best Practices

1. **Always test first** - Use dry-run mode before running against production data
2. **Check logs** - Review `[DRY-RUN]` messages to understand what would happen
3. **Combine with ephemeral** - Use `--dry-run --ephemeral` for fastest testing
4. **Monitor output** - Verify business logic produces expected results
5. **Remove for production** - Never leave dry-run enabled in production cron jobs

## Error Handling

- Dry-run mode is fail-safe - it defaults to preventing writes if there's any uncertainty
- Database connection errors still occur in dry-run mode (for read operations)
- Configuration issues are still detected and reported
- Network problems accessing external APIs will still cause failures

## Implementation Details

The dry-run functionality is implemented at the database operation level, with checks added before every write operation:

```python
if self.dry_run:
    logger.info("[DRY-RUN] Skipping database operation")
    return
# Normal database operation continues only if not in dry-run mode
```

This ensures that even if new database operations are added in the future, they'll automatically be protected if the pattern is followed.
