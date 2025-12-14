# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
KC New Restaurants Monitor is an automated system that scrapes Kansas City business license data, filters for food-related businesses, enriches records with Google Places API data and health inspection grades, generates AI-powered rating predictions using PyTorch, and sends email alerts for new establishments.

## Common Development Commands

### Running the Application
```bash
# Standard execution (checks for new restaurants)
python3 "KC New Restaurants.py"

# Dry-run mode (safe testing, no database changes)
python3 "KC New Restaurants.py" --dry-run --nodelay

# Ephemeral mode (no database connection)
python3 "KC New Restaurants.py" --ephemeral --nodelay

# Flush database and rebuild
python3 "KC New Restaurants.py" --flush

# Disable Google Places enrichment (faster)
python3 "KC New Restaurants.py" --no-enrichment
```

### Testing
```bash
# Run dry-run test suite
python3 tests/test_dry_run.py

# Test Google Places integration
python3 tests/test_google_places.py

# Test sentiment analysis integration
python3 tests/test_sentiment_integration.py

# Test health inspection integration
python3 tests/test_health_inspection.py
```

### Database Operations
```bash
# Query restaurant count
bash query_restaurants.sh count

# Show restaurants by business type
bash query_restaurants.sh types

# Show recent additions (last N days)
bash query_restaurants.sh recent 30

# Search by name
bash query_restaurants.sh search "pizza"

# Show all bakeries
bash query_restaurants.sh bakeries

# Show mobile food services
bash query_restaurants.sh mobile

# Open interactive MongoDB shell
bash query_restaurants.sh custom
```

### Google Places Enrichment
```bash
# Run enrichment job for restaurants missing Google data
python3 enrichment_job.py

# Check API usage and costs
python3 check_api_usage.py

# Database status and enrichment progress
python3 database_status_check.py
```

### Database Migration
```bash
# Migrate database schema (when schema changes)
python3 migrate_database_schema.py
```

## Architecture

### Core Application Flow
1. **Data Acquisition**: `download_kc_business_csv()` scrapes KC Business License Search portal
2. **Filtering**: `process()` filters for food businesses (FOOD_BUSINESS_TYPES) in current year
3. **Duplicate Detection**: `exists()` checks compound index (business_name + address + business_type)
4. **Enrichment**: `enrich_restaurant_data()` fetches Google Places data and AI predictions
5. **Persistence**: MongoDB insertion with automatic enrichment
6. **Notification**: `send_email_alert()` generates HTML email with AI grades

### Key Classes and Modules

#### Main Application (`KC New Restaurants.py`)
- **KCRestaurant**: Primary orchestrator class
  - Manages MongoDB connection (with SQLite fallback via DatabaseManager)
  - Initializes GooglePlacesClient for enrichment
  - Tracks statistics: total_records, new_businesses, enrichment_success/failed
  - `dry_run` mode: All write operations skipped with [DRY-RUN] log prefix

#### Service Layer (`services/`)
- **GooglePlacesClient** (`google_places_client.py`): Google Places API (New v2024) integration
  - Rate limiting: default 8 req/s
  - Caching to minimize API costs
  - Returns PlaceData objects with 20+ enrichment fields
  - Integrates AI predictions and health inspection grades automatically
  
- **HealthInspectionClient** (`health_inspection_client.py`): KC Health Department inspection scraper
  - Scrapes inspectionsonline.us for restaurant health grades
  - Calculates letter grades based on critical and non-critical violations
  - Grading: 1 critical = C, 2 critical = D, 3+ critical = F (and beyond)
  - Non-critical penalty: every 3 violations = -1 grade letter
  - Averages across all available inspections
  
- **DatabaseManager** (`database_manager.py`): Dual persistence layer
  - Primary: MongoDB (cloud/local)
  - Fallback: SQLite (when MongoDB unavailable)
  - Automatic failover between backends
  
- **SentimentAnalyzer** (`sentiment_analyzer.py`): NLP review analysis
  - TextBlob-based sentiment scoring
  - Keyword extraction from reviews
  - Generates sentiment summaries
  
- **AIPredctor** (`ai_predictor.py`): ML rating prediction
  - Loads PyTorch model for inference
  - Features: location, business_type, cuisine, amenities, price_level
  - Outputs: predicted rating (1-5), letter grade (A+ to F), confidence score

#### Machine Learning (`ml/`)
- **model.py**: PyTorch neural network architecture
  - 4-layer network: 128→64→32→1 neurons
  - Dropout for regularization
  - Input: location, business attributes, amenities
  - Output: Rating prediction (1-5 scale)
  
- **grading.py**: Letter grade conversion
  - Maps ratings to A+ through F grades
  - Color coding for email presentation

#### Utilities (`utils/`)
- **retry_utils.py**: Exponential backoff and error handling
  - Used by Google Places API for rate limiting
  - Configurable retry strategies

### Data Schema

#### MongoDB Collection: `kansas_city.food_businesses`
Core fields (KC License Data):
- `business_name`, `dba_name`, `address`, `business_type`, `valid_license_for`
- `insert_date` (ISO timestamp), `deleted` (soft delete flag)

Google Places Enhancement (20+ fields):
- `google_place_id`, `google_rating`, `google_review_count`
- `latitude`, `longitude`, `cuisine_type`, `price_level`
- Amenities: `outdoor_seating`, `takeout_available`, `delivery_available`, `wheelchair_accessible`, etc.
- `business_hours`, `review_summary`, `places_last_updated`

AI Prediction Fields:
- `ai_predicted_rating`, `ai_predicted_grade`, `ai_prediction_confidence`
- `ai_confidence_percentage`, `ai_confidence_level`, `ai_prediction_explanation`
- `ai_similar_restaurants_count`

Health Inspection Fields:
- `health_inspection_grade`, `health_avg_critical`, `health_avg_noncritical`
- `health_total_inspections`, `health_last_inspection_date`
- `health_grade_explanation`

Indexes:
- Compound unique: `{business_name: 1, address: 1, business_type: 1}` (supports franchises)
- Query optimization: `{insert_date: 1}`, `{google_place_id: 1}`

### Environment Variables
Required:
```bash
export mongodb_uri="mongodb+srv://username:password@cluster.mongodb.net/"
export gmail_sender_email="your-email@gmail.com"
export gmail_sender_password="your-app-password"
export gmail_recipient_email="alerts@your-domain.com"
export GOOGLE_PLACES_API_KEY="your-google-places-api-key"
```

Optional:
```bash
export GOOGLE_PLACES_REGION="us"  # Region bias for searches
```

### Dry-Run Mode Safety
When `--dry-run` flag is set:
- MongoDB operations are **simulated only** (logged with [DRY-RUN] prefix)
- Protected operations: `insert_one()`, `delete_many()`, `drop_index()`, `create_index()`
- Read operations still execute (for duplicate detection)
- Email alerts still send (to verify email template)
- Processing logic fully executes
- Combine with `--ephemeral` for maximum safety (no DB connection)

### Food Business Types Filter
The system tracks these business categories (stored in `FOOD_BUSINESS_TYPES` frozen set):
- Full-Service Restaurants
- Limited-Service Restaurants  
- Mobile Food Services
- Retail Bakeries
- Supermarkets and Other Grocery Retailers
- All Other Specialty Food Retailers
- Cafeterias Grill Buffets and Buffets
- Snack and Nonalcoholic Beverage Bars
- Food (Health) Supplement Retailers
- Confectionery and Nut Retailers

### Logging and Security
- Log directory: `log/` (created automatically)
- MongoDB URIs sanitized before logging (credentials removed)
- Email addresses masked in logs (first 2 chars visible)
- Google API keys never logged

## Development Patterns

### Adding New Business Types
Edit `FOOD_BUSINESS_TYPES` frozen set in main script. Match exact strings from KC portal.

### Modifying Enrichment Fields
1. Update `PlaceData` class in `services/google_places_client.py`
2. Update `enrich_restaurant_data()` in main script to store new fields
3. Update `place_data_to_dict()` in `enrichment_job.py` for batch processing
4. Consider schema migration via `migrate_database_schema.py`

### Testing Changes Safely
Always test with dry-run mode first:
```bash
# Test against production data without modification
python3 "KC New Restaurants.py" --dry-run --nodelay

# Test without any DB connection
python3 "KC New Restaurants.py" --dry-run --ephemeral --nodelay
```

### Backup Strategy
Repository uses automatic file backups:
- Location: `backup/` and `backups/` directories
- Dated copies: `{name}.{iso-8601 date}.{ext}` format
- Retention: Max 50 copies for files <150KB, 25 for larger files
- Triggered: Before git push or major changes

### Cron Deployment
Use wrapper script for enhanced logging:
```bash
crontab -e
# Daily at 8 AM
0 8 * * * /path/to/run_kc_restaurants_cron.sh

# Alternative: Direct execution with logging
0 8 * * * cd /path/to/KC-New-Restaurants && python3 "KC New Restaurants.py" >> /var/log/kc-restaurants-cron.log 2>&1
```

Script includes built-in random delay (1-15 minutes) when running under cron to distribute server load. Skip with `--nodelay` flag if needed.

## Code Style (User Preferences)
- **Semicolons**: End all statements with `;` even in Python
- **Spacing**: Spaces inside parentheses/brackets: `print( "text" );`
- **Line Length**: Prefer long lines over PEP8 80-character limit
- **Portmanteau**: When combining words with shared letters, merge them: "useroaming" for "user roaming"

## Git Workflow
This repository is stored under `/ARCHIVE/Programming/KC-New-Restaurants`.

Standard workflow:
1. Make changes and test with dry-run mode
2. Run tests: `python3 tests/test_dry_run.py`
3. Create backup copies of modified files (automatic per user rules)
4. Commit changes with descriptive message
5. Push to remote (SSH for this repo)

Note: DO NOT automatically add/commit/push without explicit user request. Show changes and ask for confirmation.

## Important Notes
- **Google API Costs**: ~$3-5/month with $200 free monthly credit (~40,000 requests)
- **Rate Limiting**: GooglePlacesClient defaults to 8 req/s (configurable)
- **Caching**: Google Places data cached locally to minimize API calls
- **Duplicate Prevention**: Compound index prevents duplicates while supporting franchises (same name, different locations)
- **Email**: Requires Gmail App Password (not regular password) with 2FA enabled
- **Database Failover**: System uses SQLite if MongoDB unavailable (via DatabaseManager)
- **Machine Learning**: PyTorch model trains weekly, predictions run after Google Places enrichment

## File Organization
- **Root**: Main application script, job runners, shell utilities
- **backup/**: Manual backup copies
- **backups/**: Automated dated backup copies  
- **data/**: CSV downloads and temporary data
- **docs/**: Additional documentation
- **logs/**: Application logs (auto-created)
- **ml/**: Machine learning models and training scripts
- **services/**: API integrations and business logic
- **tests/**: Test suites
- **utils/**: Shared utility functions
