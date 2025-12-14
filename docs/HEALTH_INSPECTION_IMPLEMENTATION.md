# Health Inspection Integration

## Overview
Added Kansas City Health Department inspection grade integration to the restaurant monitoring system. Health grades now appear alongside AI-predicted "Expected Enjoyment" ratings in email alerts.

## Implementation Details

### New Components

#### 1. Health Inspection Client (`services/health_inspection_client.py`)
- **Purpose**: Scrapes health inspection data from inspectionsonline.us
- **Features**:
  - POST search to Kansas City health inspection portal
  - Parses inspection records (date, critical violations, non-critical violations)
  - Calculates letter grades based on violation averages
  - Rate limiting to respect server load

#### 2. Grading Algorithm
**Starting point**: Grade A

**Critical violations penalty**:
- 1 critical violation → Grade C
- 2 critical violations → Grade D
- 3 critical violations → Grade F
- 4+ critical violations → Continue past F (G, H, I, etc.)

**Non-critical violations penalty**:
- Every 3 non-critical violations → -1 grade letter
- Example: 6 non-critical violations = -2 grade letters

**Averaging**: Grades are calculated based on average violations across all available inspections

### Integration Points

#### 1. Data Model (`PlaceData`)
Added health inspection fields to `PlaceData` class:
```python
health_inspection_grade: Optional[str]
health_avg_critical: Optional[float]
health_avg_noncritical: Optional[float]
health_total_inspections: Optional[int]
health_last_inspection_date: Optional[str]
health_grade_explanation: Optional[str]
```

#### 2. GooglePlacesClient Enhancement
- Added `enable_health_inspections` parameter (default: `True`)
- Initializes `HealthInspectionClient` during setup
- Fetches health grades automatically in `enrich_restaurant_data()`
- Health inspection failures are non-blocking (logged as warnings)

#### 3. Database Schema
New fields added to MongoDB documents:
- `health_inspection_grade`
- `health_avg_critical`
- `health_avg_noncritical`
- `health_total_inspections`
- `health_last_inspection_date`
- `health_grade_explanation`

#### 4. Email Template
Updated `generate_email_html()` to display dual grades:
- **Left column**: AI Predicted "Expected Enjoyment" grade (existing)
- **Right column**: Health Inspection grade (NEW)
- Both displayed side-by-side in responsive layout
- Health grade shows last inspection date
- Tooltip shows grade explanation on hover

### Usage

#### Running with Health Inspections
```bash
# Standard execution (health inspections enabled by default)
python3 "KC New Restaurants.py"

# Disable health inspections if needed
# (Requires code modification - no CLI flag yet)
```

#### Testing Health Inspection Client
```bash
# Test health inspection scraping
python3 tests/test_health_inspection.py

# Test with specific restaurant
python3 -c "from services.health_inspection_client import HealthInspectionClient; \
client = HealthInspectionClient(); \
grade = client.get_health_grade('Joe\\'s Kansas City', '3002 W 47th Ave'); \
print(f'Grade: {grade.letter_grade}' if grade else 'Not found')"
```

### Dependencies
Added to `requirements.txt`:
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - HTML parser backend

Install with:
```bash
pip install beautifulsoup4 lxml
```

### Configuration
No environment variables required. Health inspection client:
- Uses public KC health inspection portal
- Rate limited to 1 request/second (configurable)
- Automatically retries on transient failures

### Email Display Example
```
┌─────────────────────────────────────────────┐
│  Joe's Kansas City Bar-B-Que                │
│  3002 W 47th Ave, Kansas City, KS           │
│                                             │
│  ┌──────────────┬──────────────────────┐   │
│  │  Expected    │  Health Grade        │   │
│  │  Enjoyment   │                      │   │
│  │  4.7         │       A+             │   │
│  │  A+          │  Last: 11/15/2024    │   │
│  │  85% conf.   │  Health Grade        │   │
│  └──────────────┴──────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Error Handling
- Health inspection failures are **non-blocking**
- Restaurants without inspection data show "N/A" in health grade column
- Network errors are logged as warnings
- Search failures don't prevent email alerts

### Performance Impact
- Adds ~1-2 seconds per restaurant for health grade lookup
- Rate limited to avoid overwhelming inspection portal
- Runs in parallel with other enrichment (Google Places)

### Future Enhancements
Potential improvements:
1. Cache health inspection results in MongoDB
2. Background job to update health grades periodically
3. CLI flag to disable health inspections (`--no-health-inspections`)
4. Display individual inspection details in email
5. Alert on failing health grades
6. Historical health grade trending

### Files Modified
1. `services/health_inspection_client.py` - NEW
2. `services/google_places_client.py` - Modified (added health integration)
3. `KC New Restaurants.py` - Modified (email template, data storage)
4. `requirements.txt` - Updated (added beautifulsoup4, lxml)
5. `WARP.md` - Updated (documentation)
6. `tests/test_health_inspection.py` - NEW

### Testing Checklist
- [x] Health inspection client can search for restaurants
- [x] Grading algorithm calculates correct letter grades
- [x] Integration with GooglePlacesClient works
- [x] Email template displays both grades correctly
- [x] Database stores health inspection fields
- [x] Error handling prevents blocking on failures
- [ ] End-to-end test with real restaurant data (TODO)
- [ ] Verify email formatting on mobile devices (TODO)

## Notes
- The KC health inspection portal uses POST forms, not REST APIs
- HTML parsing may be fragile if portal changes structure
- Some restaurants may not have inspection data (new businesses)
- Inspection data is public record per KC Health Department
