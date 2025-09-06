# KC New Restaurants Monitor Architecture

## Project Overview
Automated Kansas City food business license tracking system with Google Places API integration and AI-powered restaurant rating prediction.

## System Components

### 1. Core Application (`KC New Restaurants.py`)
- **Purpose**: Main application for downloading KC business license data, processing food businesses, and sending email alerts
- **Key Features**:
  - Web scraping of KC Business License Search portal
  - CSV data parsing and validation
  - MongoDB persistence with duplicate detection
  - HTML email generation and SMTP delivery
  - Dry-run mode for testing
  - Comprehensive logging and error handling

### 2. Database Schema (MongoDB)

#### Current Production Schema (`kansas_city.food_businesses`)
**Status**: ✅ **379 active documents** | **No Google Places data** | **Ready for migration**

```json
{
  "_id": "ObjectId - MongoDB document ID",
  "business_name": "String - Official business name (indexed)",
  "dba_name": "String - 'Doing Business As' name", 
  "address": "String - Full business address (indexed)",
  "business_type": "String - Type from FOOD_BUSINESS_TYPES (indexed)",
  "valid_license_for": "String - License year (e.g., '2025')",
  "insert_date": "String - ISO timestamp when added to DB (indexed)",
  "deleted": "Boolean - Soft delete flag (always False currently)"
}
```

**Current Indexes**:
- `_id_` (default MongoDB index)
- `insert_date_1` (query optimization for recent records)
- `business_name_1_address_1_business_type_1` (compound unique index for duplicates)

#### Enhanced Schema (Post-Google Places Integration)
```json
{
  // Original KC License Data
  "business_name": "String",
  "dba_name": "String", 
  "address": "String",
  "business_type": "String",
  "valid_license_for": "String",
  "insert_date": "String",
  "deleted": "Boolean",
  
  // Google Places Data
  "google_place_id": "String - Unique Google identifier",
  "google_rating": "Number - Google rating (1-5 scale)",
  "google_review_count": "Number - Total number of reviews",
  "price_level": "Number - Cost indicator (0-4: Free, $, $$, $$$, $$$$)",
  "latitude": "Number - Geographic latitude",
  "longitude": "Number - Geographic longitude", 
  "cuisine_type": "String - Primary cuisine (Mexican, American, Chinese, etc.)",
  "outdoor_seating": "Boolean - Has outdoor seating",
  "takeout_available": "Boolean - Offers takeout service",
  "delivery_available": "Boolean - Offers delivery service", 
  "reservations_accepted": "Boolean - Accepts reservations",
  "wheelchair_accessible": "Boolean - Wheelchair accessible entrance",
  "good_for_children": "Boolean - Child-friendly establishment",
  "serves_alcohol": "Boolean - Serves beer/wine",
  "parking_available": "Boolean - Parking available",
  "business_hours": "Object - Operating hours structure",
  "review_summary": "String - Summary of recent reviews (top 3)",
  "places_last_updated": "String - ISO timestamp of last Google data fetch",
  
  // AI Model Predictions
  "ai_predicted_rating": "Number - ML predicted rating (1-5 scale)",
  "ai_predicted_grade": "String - Letter grade (A+, A, A-, B+, B, B-, C+, C, C-, D, F)",
  "prediction_confidence": "Number - Model confidence score (0-1)",
  "model_version": "String - Version of ML model used",
  "prediction_date": "String - ISO timestamp of prediction",
  "features_used": "Object - Input features used for prediction"
}
```

#### Indexes
- **Unique Compound**: `{business_name: 1, address: 1, business_type: 1}`
- **Query Optimization**: `{insert_date: 1}`, `{google_place_id: 1}`

### 3. Business Types Filter
Current `FOOD_BUSINESS_TYPES` includes:
- Full-Service Restaurants
- Limited-Service Restaurants
- Mobile Food Services  
- Retail Bakeries
- All Other Specialty Food Retailers
- Supermarkets and Other Grocery Retailers
- Cafeterias Grill Buffets and Buffets
- Snack and Nonalcoholic Beverage Bars
- Food (Health) Supplement Retailers
- Confectionery and Nut Retailers

### 4. Google Places API Integration

#### Service Layer (`services/google_places.py`)
- **Functions**:
  - `search_place(name, address)` - Find place by name/address
  - `get_place_details(place_id)` - Get comprehensive place data
  - `extract_amenities(place_data)` - Parse amenities from place data
  - `determine_cuisine_type(place_data)` - Extract primary cuisine
  - `get_review_summary(reviews)` - Summarize top 3 reviews

#### API Data Fields Retrieved
- **Basic**: place_id, name, formatted_address, geometry.location, types
- **Ratings**: rating, user_ratings_total, price_level
- **Amenities**: Various boolean flags parsed from place attributes
- **Reviews**: Limited to top 3 recent reviews for summary

#### Rate Limiting & Error Handling
- Exponential backoff for API failures
- Respect Google's rate limits (typically 100 requests/second)
- Quota monitoring with $200 monthly credit (~40,000 requests)
- Graceful degradation when API unavailable

### 5. Machine Learning Pipeline

#### Model Architecture (`ml/model.py`)
**PyTorch Neural Network**:
```python
class RestaurantRatingPredictor(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64), 
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(), 
            nn.Linear(32, 1),
            nn.Sigmoid()  # Output 0-1, scaled to 1-5 rating
        )
```

#### Features for Training
1. **Location**: latitude, longitude, normalized distance from city center
2. **Business Type**: One-hot encoded business_type categories  
3. **Cuisine**: One-hot encoded cuisine_type categories
4. **Amenities**: Binary flags (outdoor_seating, takeout, delivery, etc.)
5. **Price Level**: Normalized 0-1 scale
6. **Operational**: Business hours, days open per week

#### Target Variable
- Google rating (1-5 scale) normalized to 0-1 for training
- Letter grade mapping: A+ ≥ 4.6, A = 4.4-4.59, A- = 4.2-4.39, B+ = 4.0-4.19, etc.

#### Model Training (`ml/train.py`)
- Train/validation split: 80/20
- Loss function: MSE (Mean Squared Error)
- Optimizer: Adam with learning rate 0.001
- Early stopping based on validation loss
- Model checkpointing and versioning

#### Prediction Pipeline (`ml/predict_batch.py`)
- Batch processing of new restaurants
- Feature preprocessing and scaling
- CUDA/CPU device selection
- Confidence scoring based on model uncertainty
- Database update with predictions

### 6. Data Processing Workflows

#### Daily Processing Flow
1. **KC License Data Ingestion** (`KC New Restaurants.py`)
   - Download CSV from KC Business License portal
   - Filter for current year food businesses  
   - Check for duplicates in MongoDB
   - Insert new businesses with original schema

2. **Google Places Enhancement** (`jobs/refresh_google_data.py`)
   - Query new businesses lacking Google data
   - Call Google Places API for each business
   - Parse and store enhanced data fields
   - Update businesses with Google information

3. **AI Prediction Generation** (`ml/predict_batch.py`)
   - Load trained PyTorch model
   - Extract features for businesses lacking predictions
   - Generate rating predictions and confidence scores
   - Update database with AI predictions

4. **Email Alert Generation** 
   - Generate HTML email with enhanced data
   - Include AI predictions prominently in template
   - Send via SMTP to configured recipients

#### Migration Strategy
- **Phase 1**: Add new columns to existing collection (non-breaking)
- **Phase 2**: Backfill Google Places data for existing restaurants
- **Phase 3**: Train initial ML model on populated dataset
- **Phase 4**: Deploy AI predictions to production emails

### 7. Email System Enhancement

#### Enhanced HTML Template
```html
<table>
  <tr>
    <td>
      <h3><a href="{google_link}">{restaurant_name}</a></h3>
      <p>{address}</p>
      <p>Type: {business_type} | Cuisine: {cuisine_type}</p>
      <p>Amenities: {amenities_list}</p>
    </td>
    <td style="text-align: right; vertical-align: middle;">
      <h1 style="font-size: 48px; margin: 0;">{ai_predicted_rating}</h1>
      <h2 style="font-size: 36px; margin: 0; color: {grade_color};">{ai_predicted_grade}</h2>
      <small>AI Predicted</small>
    </td>
  </tr>
</table>
```

#### Styling Enhancements
- Large, prominent display of AI rating and grade
- Color coding for grade levels (A+ = green, C- = orange, F = red)
- Responsive table layout for mobile devices
- Fallback display when predictions unavailable

### 8. Configuration Management

#### Environment Variables
```bash
# Existing
mongodb_uri="mongodb://username:password@host:port/database"
gmail_sender_email="sender@gmail.com"
gmail_sender_password="app_specific_password"
gmail_recipient_email="recipient@email.com"

# New for Google Places
GOOGLE_PLACES_API_KEY="your_google_places_api_key"
GOOGLE_PLACES_REGION="us"  # Bias search results to US

# ML Model Configuration  
ML_MODEL_PATH="./models/restaurant_predictor.pt"
ML_DEVICE="cuda"  # or "cpu" for fallback
ML_CONFIDENCE_THRESHOLD="0.7"  # Minimum confidence for displaying predictions
```

### 9. Testing Strategy

#### Unit Tests
- **API Layer**: Mock Google Places responses, test data parsing
- **ML Pipeline**: Test feature engineering, model loading, predictions
- **Database**: Test schema validation, migrations, queries
- **Email**: Test HTML generation with various data scenarios

#### Integration Tests  
- **End-to-End**: KC data → Google Places → ML prediction → Email
- **API Integration**: Real Google Places API calls (development key)
- **Database Integration**: Full CRUD operations with test data
- **Email Integration**: Test email delivery (test recipients)

#### Performance Tests
- **API Rate Limiting**: Test backoff and retry logic
- **Database Load**: Test with large datasets (10k+ restaurants)
- **ML Inference**: Benchmark prediction speed on CPU vs GPU

### 10. Deployment & Operations

#### Dependencies
```txt
# Existing
pymongo>=4.0.0
requests>=2.25.0

# New Dependencies  
torch>=2.0.0
pandas>=1.3.0
scikit-learn>=1.0.0
googlemaps>=4.10.0  # Google Places API client
numpy>=1.21.0
```

#### Scheduled Jobs (Cron)
```bash
# Existing: Daily KC data processing
0 2 * * * cd /path/to/project && python3 "KC New Restaurants.py"

# New: Google Places data refresh (after KC processing)
0 3 * * * cd /path/to/project && python3 jobs/refresh_google_data.py

# New: AI predictions update (after Google data)
0 4 * * * cd /path/to/project && python3 ml/predict_batch.py

# Weekly: Retrain ML model with new data
0 5 * * 0 cd /path/to/project && python3 ml/train.py
```

#### Monitoring & Alerting
- **Google API Quota**: Monitor daily usage against $200 credit
- **Model Performance**: Track prediction accuracy over time
- **Database Growth**: Monitor collection size and index performance
- **Email Delivery**: Track successful email sends and bounces

### 11. Security Considerations

#### API Key Management
- Store Google Places API key in environment variables only
- Restrict API key to specific IP addresses and domains
- Enable HTTP referrer restrictions in Google Cloud Console
- Regular key rotation (quarterly)

#### Database Security
- Use MongoDB connection strings with authentication
- Implement proper network security (VPN, firewall rules)
- Regular database backups with encryption
- Monitor for unusual query patterns

#### Email Security
- Use Gmail App Passwords instead of main account password
- Enable 2FA on Gmail account
- Sanitize all user input in email templates
- Rate limiting on email sends to prevent spam

#### Logging Security
- All MongoDB URIs are sanitized before logging to prevent credential exposure
- Email addresses are masked in logs (showing only first 2 characters)
- Sensitive configuration values should never appear in plain text logs
- Regular cleanup of old log files to prevent credential leakage

### 12. Known Issues & Future Enhancements

#### Current Limitations
- Google Places API quota limiting (~40k requests/month with free tier)
- ML model training requires significant historical data
- Email template not optimized for all mobile clients
- No web interface for viewing restaurant data

#### Planned Enhancements
- **Web Dashboard**: Flask/FastAPI web interface for restaurant browsing
- **Real-time Updates**: WebSocket notifications for new restaurants
- **Advanced ML**: Ensemble models, time-series prediction
- **Geographic Analysis**: Heat maps of restaurant quality by neighborhood
- **User Feedback**: Allow users to rate prediction accuracy

### 13. Development Workflow

#### Git Branch Strategy
- `main` - Production ready code
- `develop` - Integration branch for features  
- `feat/google-places-ml-email` - Current feature branch

#### Code Quality
- **Formatting**: Follow user's style preferences (spaces in brackets, semicolons, long lines)
- **Testing**: Maintain >90% code coverage
- **Documentation**: Update architecture.md with each major feature
- **Type Hints**: Use Python type annotations throughout

#### Release Process
1. Feature development in feature branch
2. Unit and integration testing
3. Code review and architecture.md updates
4. Merge to develop branch
5. Staging deployment and testing
6. Merge to main and production deployment

---

*Last updated: 2024-12-19*
*Version: 2.0 (Google Places + AI Integration)*
