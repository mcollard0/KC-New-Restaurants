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

### Indexes
- **Unique Compound Index**: `(business_name, address, business_type)` - Prevents duplicates while supporting franchises
- **Query Index**: `(insert_date)` - Optimizes time-based queries and reporting

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
```

### Email Setup (Gmail)
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password (Security → App passwords)
3. Use the 16-character app password (not your regular password)

## 🔧 Installation

### Prerequisites
```bash
# Python dependencies
sudo apt install python3-pymongo python3-requests

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

*As of latest run:*
- **Total Tracked**: 379+ food businesses
- **Business Types**: 10 different categories  
- **Coverage**: All of Kansas City, Missouri
- **Update Frequency**: Daily monitoring available
- **Alert Speed**: Near real-time notifications

---

**Made with ❤️ for Kansas City food lovers**
