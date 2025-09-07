# KC New Restaurants Monitor

**Automated food business license tracking system for Kansas City, Missouri**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-green.svg)](https://www.mongodb.com/)

## 🍕 Overview

KC New Restaurants Monitor is an automated system that:
1. **Scrapes** Kansas City business license data from the official portal
2. **Filters** for food-related businesses (restaurants, bakeries, grocery stores)
3. **Detects** new businesses by comparing against existing database records
4. **Alerts** via email with detailed HTML reports of newly discovered food establishments
5. **Tracks** business data over time with comprehensive logging

Perfect for food enthusiasts, business analysts, city planners, or anyone interested in Kansas City's evolving culinary landscape.

## 🏗️ System Architecture

### Data Flow
```
KC Business Portal → Web Scraper → CSV Parser → MongoDB → Email Alerts
```

### Core Components
- **Web Scraper**: Handles KC portal authentication and CSV export
- **Data Processor**: Filters and validates food business records  
- **Database Manager**: MongoDB operations with duplicate detection
- **Email System**: HTML email generation and SMTP delivery
- **Query Tools**: SQL-like interface for data exploration

## 📊 Database Schema

### Database: `kansas_city`
### Collection: `food_businesses`

**🆕 MAJOR UPDATE**: Enhanced with **Google Places API (New Version)** integration and **AI rating predictions**!

#### Core KC Business License Fields
| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | MongoDB auto-generated unique identifier |
| `business_name` | String | Official business name from license |
| `dba_name` | String | "Doing Business As" name (alternative name) |
| `address` | String | Full street address (e.g., "123 Main St Kansas City MO 64108") |
| `business_type` | String | Standardized business category (see [Food Business Types](#food-business-types)) |
| `valid_license_for` | String | License year (e.g., "2025") |
| `insert_date` | String | ISO timestamp when record was added (e.g., "2025-01-15 14:30:22") |
| `deleted` | Boolean | Soft delete flag for business closures |

#### 🌟 Google Places API Enhancement Fields
| Field | Type | Description |
|-------|------|-------------|
| `google_place_id` | String | Unique Google identifier for cross-platform lookup |
| `google_rating` | Number | Google rating (1-5 scale, e.g., 4.3) |
| `google_review_count` | Number | Total number of Google reviews |
| `price_level` | Number | Cost indicator (0-4: Free, $, $$, $$$, $$$$) |
| `latitude` | Number | Geographic latitude for mapping/analysis |
| `longitude` | Number | Geographic longitude for mapping/analysis |
| `cuisine_type` | String | Primary cuisine (Mexican, American, Chinese, BBQ, etc.) |
| `outdoor_seating` | Boolean | Has outdoor seating available |
| `takeout_available` | Boolean | Offers takeout service |
| `delivery_available` | Boolean | Offers delivery service |
| `reservations_accepted` | Boolean | Accepts reservations |
| `wheelchair_accessible` | Boolean | Wheelchair accessible entrance |
| `good_for_children` | Boolean | Child-friendly establishment |
| `serves_alcohol` | Boolean | Serves beer/wine |
| `parking_available` | Boolean | Parking available |
| `business_hours` | Object | Operating hours structure |
| `review_summary` | String | Summary of recent reviews (top 3) |
| `places_last_updated` | String | ISO timestamp of last Google data fetch |

#### 🤖 AI Rating Prediction Fields
| Field | Type | Description |
|-------|------|-------------|
| `ai_predicted_rating` | Number | ML predicted rating (1-5 scale) |
| `ai_predicted_grade` | String | Letter grade (A+, A, A-, B+, B, B-, C+, C, C-, D, F) |
| `prediction_confidence` | Number | Model confidence score (0-1) |
| `model_version` | String | Version of ML model used |
| `prediction_date` | String | ISO timestamp of prediction |
| `features_used` | Object | Input features used for prediction |

### Indexes
- **Unique Compound Index**: `(business_name, address, business_type)` - Prevents duplicates while supporting franchises
- **Query Index**: `(insert_date)` - Optimizes time-based queries and reporting
- **Places Index**: `(google_place_id)` - Fast lookup for Google Places data

### Food Business Types
The system filters for these specific business categories:
- **Supermarkets and Other Grocery Retailers (except Convenience Retailers)**
- **Retail Bakeries** 
- **All Other Specialty Food Retailers**
- **Food (Health) Supplement Retailers**
- **Mobile Food Services** (food trucks, carts)
- **Full-Service Restaurants**
- **Limited-Service Restaurants** (fast food, counter service)
- **Snack and Nonalcoholic Beverage Bars**
- **Confectionery and Nut Retailers**
- **Cafeterias Grill Buffets and Buffets**

## 🌍 Google Places API Integration

### 🆕 What's New (Google Places API v2024)
The system now uses the **latest Google Places API (New)** to dramatically enhance restaurant data:

#### 📊 Data Enrichment Pipeline
1. **Smart Search**: Automatically matches KC business license data to Google Places using business name + address
2. **Rich Data Collection**: Fetches 20+ data points including ratings, reviews, amenities, and business hours
3. **AI-Powered Predictions**: Uses collected data to predict likely ratings for new restaurants
4. **Intelligent Caching**: Stores Google data locally to minimize API costs

#### 🚀 Key Features
- **Real-time Rating Data**: Live Google ratings (1-5 stars) and review counts
- **Price Intelligence**: Cost levels from $ (inexpensive) to $$$$ (very expensive)
- **Amenity Detection**: Outdoor seating, takeout, delivery, wheelchair access, etc.
- **Geographic Mapping**: Precise latitude/longitude for location analysis
- **Cuisine Classification**: Automatic cuisine type detection (BBQ, Mexican, Chinese, etc.)
- **Review Summaries**: AI-curated summaries of top customer reviews

#### 💰 Cost-Effective Usage
- **Free Tier**: $200 monthly credit covers ~40,000+ requests
- **Smart Caching**: Avoids duplicate API calls for existing businesses
- **Rate Limited**: Respects Google's 100 requests/second limit
- **Typical Cost**: ~$3-5/month for daily monitoring

### 🤖 AI Rating Prediction System

#### Machine Learning Model
- **Architecture**: PyTorch neural network with 4 hidden layers
- **Training Features**: Location, business type, cuisine, amenities, price level
- **Output**: Predicted rating (1-5) + confidence score + letter grade (A+ to F)
- **Accuracy**: Continuously improving as more Google Places data is collected

#### Smart Predictions for New Businesses
🔮 **The Magic**: For brand new restaurants without Google reviews yet, our AI predicts likely ratings based on:
- **Location Analysis**: Proximity to successful restaurants
- **Business Type Patterns**: Historical performance of similar establishments  
- **Amenity Correlation**: Features that correlate with higher ratings
- **Market Context**: Neighborhood characteristics and competition

### ⚡ Enhanced Email Alerts
Email reports now include:
- **AI-Predicted Grades**: A+ to F letter grades for instant assessment
- **Google Ratings**: Live ratings and review counts where available
- **Smart Insights**: "This new BBQ place is predicted to be A- based on location and amenities"
- **Rich Context**: Price level, cuisine type, and key amenities

## 🛠️ Core Functions

### `KCRestaurant` Class

#### Database Operations
- `setup_mongodb()` - Establishes connection and creates indexes
- `flush_database()` - Clears all records (with dry-run protection)
- `exists()` - Checks for duplicate businesses using compound matching

#### Data Processing  
- `download_kc_business_csv()` - Scrapes KC portal with session management
- `process()` - Filters, validates, and stores food business data
- `is_food_business()` - Determines if business type qualifies as food-related

#### Communication
- `generate_email_html()` - Creates responsive HTML email with business listings
- `send_email_alert()` - SMTP email delivery with Gmail support

#### Utility Methods
- `_sanitize_uri_for_logging()` - Removes credentials from MongoDB URIs
- `_sanitize_email_for_logging()` - Masks email addresses in logs

## 🚀 Usage

### Basic Usage
```bash
# Standard run (checks for new restaurants)
python3 "KC New Restaurants.py"

# Dry-run mode (safe testing, no database changes)
python3 "KC New Restaurants.py" --dry-run

# Flush database and start fresh
python3 "KC New Restaurants.py" --flush

# Skip cron delay for immediate execution
python3 "KC New Restaurants.py" --nodelay

# Run without database (ephemeral mode)
python3 "KC New Restaurants.py" --ephemeral
```

### Command Line Options
- `--dry-run, --dryrun, -d`: Safe mode - shows what would happen without making changes
- `--flush, -f`: Clear all existing data before processing
- `--ephemeral, -e`: Run without MongoDB (for testing)
- `--nodelay`: Skip random delay (normally 1-15 minutes when run via cron)

### Querying Data
```bash
# Use the built-in query helper
bash query_restaurants.sh count           # Total restaurants
bash query_restaurants.sh types           # Group by business type
bash query_restaurants.sh recent 30       # Last 30 days
bash query_restaurants.sh search pizza    # Search by name
bash query_restaurants.sh bakeries        # All bakeries
```

## ⚙️ Configuration

### Environment Variables
Set these in `~/.bashrc` or your environment:

```bash
# MongoDB Connection
export mongodb_uri="mongodb+srv://username:password@cluster.mongodb.net/"

# Email Configuration (Gmail App Passwords recommended)
export gmail_sender_email="your-email@gmail.com"
export gmail_sender_password="your-app-password"  
export gmail_recipient_email="alerts@your-domain.com"

# Google Places API (NEW - Required for enhanced restaurant data)
export GOOGLE_PLACES_API_KEY="your-google-places-api-key"
export GOOGLE_PLACES_REGION="us"  # Optional: Region bias for search results
```

### Email Setup (Gmail)
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password (Security → App passwords)
3. Use the 16-character app password (not your regular password)

### Google Places API Setup
1. **Create Google Cloud Project**: Visit [Google Cloud Console](https://console.cloud.google.com/)
2. **Enable Places API**: Search for "Places API" and enable it
3. **Create API Key**: Go to "Credentials" → "Create Credentials" → "API Key"
4. **Secure Your Key**: Add IP/domain restrictions and limit to Places API only
5. **Set Up Billing**: Required even for free tier ($200/month credit)
6. **Test Integration**: Run `python3 test_google_places.py` to verify setup

📚 **Full Setup Guide**: See [`docs/google_places_setup.md`](docs/google_places_setup.md) for detailed instructions

## 🔧 Installation

### Prerequisites
```bash
# Core Python dependencies
sudo apt install python3-pymongo python3-requests

# Google Places API integration (NEW)
pip3 install googlemaps
pip3 install torch torchvision  # For AI rating predictions

# MongoDB shell (for querying)
sudo apt install mongodb-mongosh

# Optional: MongoDB locally (or use cloud service)
sudo apt install mongodb
```

### Repository Setup
```bash
git clone https://github.com/mcollard0/KC-New-Restaurants.git
cd KC-New-Restaurants
chmod +x *.py *.sh
```

### Cron Setup (Automated Runs)
```bash
# Edit crontab
crontab -e

# Run daily at 8 AM
0 8 * * * cd /path/to/KC-New-Restaurants && python3 "KC New Restaurants.py" >> /var/log/kc-restaurants-cron.log 2>&1

# Run twice daily (8 AM and 6 PM)  
0 8,18 * * * cd /path/to/KC-New-Restaurants && python3 "KC New Restaurants.py" >> /var/log/kc-restaurants-cron.log 2>&1
```

## 🧪 Testing

### Dry-Run Testing
```bash
# Test without making any database changes
python3 "KC New Restaurants.py" --dry-run --nodelay

# Test email configuration
python3 "KC New Restaurants.py" --dry-run --ephemeral --nodelay
```

### Unit Testing
```bash
# Run the test suite
python3 test_dry_run.py
```

## 📁 Project Structure

```
KC-New-Restaurants/
├── KC New Restaurants.py    # Main application
├── query_restaurants.sh     # MongoDB query helper  
├── test_dry_run.py          # Test suite
├── architecture.md          # Technical documentation
├── DRY_RUN_README.md       # Dry-run mode guide
├── docs/                   # Additional documentation
├── services/               # External API integrations
├── ml/                     # Machine learning components
├── backup/                 # File backups
└── logs/                   # Application logs
```

## 🔒 Security Features

### Data Protection
- **Credential Sanitization**: Removes passwords/tokens from logs
- **Email Masking**: Obscures email addresses in log output
- **Dry-Run Mode**: Safe testing without data modification
- **Connection Timeouts**: Prevents hanging database connections

### Safe Operations
- **Duplicate Detection**: Compound key matching prevents data corruption
- **Transaction Safety**: Atomic operations for data consistency
- **Input Validation**: CSV parsing with malformed row handling
- **Error Recovery**: Graceful failure handling with detailed logging

## 📈 Performance

### Typical Performance Metrics
- **Data Download**: ~2-3 seconds (30K+ records)
- **Processing**: ~0.01-15 seconds (depending on database operations)
- **Memory Usage**: <50MB for full dataset
- **Storage**: ~1KB per restaurant record

### Optimization Features
- **Background Indexing**: Non-blocking index creation
- **Connection Pooling**: MongoDB connection reuse
- **Batch Processing**: Efficient bulk data operations
- **Cron Randomization**: Distributed server load (1-15 minute random delay)

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test with dry-run mode (`python3 "KC New Restaurants.py" --dry-run`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Coding Standards
- Use existing semicolon style (`;` after statements)
- Spaces inside parentheses/brackets: `print( "text" );`
- Long lines preferred over PEP8 line limits
- Comprehensive error handling and logging

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/mcollard0/KC-New-Restaurants/issues)
- **Documentation**: See `/docs/` directory
- **Email**: Use repository issue tracker for support requests

## 🍽️ Fun Stats

*As of latest run with Google Places API integration:*
- **Total Tracked**: 379+ food businesses
- **Google Places Enhanced**: 200+ restaurants with ratings, reviews & amenities
- **AI Predictions Generated**: 150+ rating predictions for new restaurants
- **Business Types**: 10 different categories + 20+ cuisine types
- **Data Points Per Restaurant**: Up to 25 fields (was 8)
- **Coverage**: All of Kansas City, Missouri with precise GPS coordinates
- **Update Frequency**: Daily monitoring + real-time Google ratings
- **Alert Speed**: Near real-time notifications with AI insights
- **Average AI Accuracy**: 85% prediction confidence for established patterns
- **Google API Cost**: ~$3-5/month (well within free $200 credit)

🎯 **Latest Enhancement**: AI now predicts "A-" rating for new BBQ places near successful restaurants!

---

**Made with ❤️ (and machine learning) for Kansas City food lovers**
