# Google Places API Setup Guide

Complete walkthrough for integrating Google Places API with KC New Restaurants Monitor.

## 🎯 Overview

Google Places API will enhance the KC New Restaurants system by:
- **Enriching restaurant data** with photos, ratings, and reviews
- **Validating business locations** with accurate address information  
- **Adding contact details** like phone numbers and websites
- **Providing business hours** and operational status
- **Enabling geographic analysis** with precise coordinates

## 🚀 Step-by-Step Setup

### Step 1: Google Cloud Console Setup

1. **Navigate to Google Cloud Console**
   ```
   https://console.cloud.google.com/
   ```

2. **Create New Project**
   - Click "Select a Project" → "New Project"
   - Project Name: `KC-New-Restaurants`
   - Organization: (your organization or leave blank)
   - Click "Create"

3. **Wait for Project Creation**
   - You'll see a notification when complete
   - The project will appear in your project selector

### Step 2: Enable Required APIs

4. **Navigate to API Library**
   - Left sidebar: "APIs & Services" → "Library"

5. **Enable Places API**
   - Search: "Places API"
   - Click "Places API" result
   - Click "Enable"

6. **Enable Additional APIs** (recommended)
   - **Geocoding API**: For address validation
   - **Maps JavaScript API**: For web integration (future)
   - **Places API (New)**: Next-generation API (if available)

### Step 3: Create and Configure API Key

7. **Generate API Key**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS"
   - Select "API key"
   - **IMPORTANT**: Copy the API key immediately!

8. **Secure the API Key** (Critical for Security)
   - Click the edit icon (✏️) next to your new API key
   
   **API Restrictions:**
   - Select "Restrict key"
   - Check these APIs:
     - ✅ Places API
     - ✅ Geocoding API  
     - ✅ Maps JavaScript API (if enabled)

   **Application Restrictions** (Choose one):
   - **IP addresses**: Add your server's public IP
   - **HTTP referrers**: For web applications
   - **Android/iOS apps**: For mobile applications
   - **None**: Less secure, not recommended for production

9. **Save Restrictions**
   - Click "Save"
   - Wait a few minutes for restrictions to take effect

### Step 4: Enable Billing (Required)

10. **Set Up Billing Account**
    - Go to "Billing" in left sidebar
    - Click "Link a billing account" or "Create billing account"
    - Enter payment information (credit/debit card)
    
11. **Understanding Costs**
    - **Free Tier**: $200/month credit (covers ~6,250 text searches)
    - **Typical Usage**: KC monitoring uses ~30 searches/day (~$1/month)
    - **Cost Control**: Set up budget alerts in billing section

### Step 5: Environment Configuration

12. **Add API Key to Environment**
    ```bash
    # Edit ~/.bashrc
    nano ~/.bashrc
    
    # Add these lines at the end
    export GOOGLE_PLACES_API_KEY="your-api-key-here"
    export GOOGLE_API_KEY="your-api-key-here"  # Alternative name
    
    # Save and reload
    source ~/.bashrc
    ```

13. **Verify Environment Setup**
    ```bash
    echo $GOOGLE_PLACES_API_KEY
    # Should show your API key
    ```

### Step 6: Test Your Setup

14. **Run the Test Script**
    ```bash
    cd "/path/to/KC New Restaurants"
    python3 test_google_places.py
    ```

15. **Expected Output**
    ```
    🚀 Google Places API Test for KC New Restaurants
    ==================================================
    🔑 Testing API key validity...
    ✅ API key is valid and working!
    🔍 Testing Places API search...
    ✅ Places search successful! Found 20 restaurants
    📋 Testing Places API details...
    ✅ Place details successful for: Joe's Kansas City Bar-B-Que
    
    ==================================================
    📊 Test Results: 3/3 tests passed
    🎉 All tests passed! Google Places API is ready to use.
    ```

## 🔧 Integration with KC New Restaurants

### Environment Variables
The system automatically detects these environment variables:
- `GOOGLE_PLACES_API_KEY` (preferred)
- `GOOGLE_API_KEY` (alternative)

### Usage in Code
```python
import os
import requests

api_key = os.getenv('GOOGLE_PLACES_API_KEY')
url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
params = {
    'query': f'{business_name} {address}',
    'key': api_key
}
response = requests.get(url, params=params)
```

## 💰 Cost Management

### Pricing (as of 2024)
- **Text Search**: $32 per 1,000 requests
- **Place Details**: $17 per 1,000 requests  
- **Geocoding**: $5 per 1,000 requests
- **Monthly Free Tier**: $200 credit

### Cost Optimization Strategies

1. **Cache API Results**
   ```python
   # Store results in MongoDB to avoid duplicate calls
   cached_place = collection.find_one({'place_id': place_id})
   if not cached_place:
       # Make API call and cache result
   ```

2. **Use Specific Fields**
   ```python
   # Only request needed fields to reduce costs
   params['fields'] = 'name,formatted_address,rating,price_level'
   ```

3. **Implement Rate Limiting**
   ```python
   import time
   time.sleep(0.1)  # 10 requests per second max
   ```

4. **Set Up Budget Alerts**
   - Go to Google Cloud Console → Billing
   - Create budget alert at $10, $25, $50
   - Enable email notifications

### Expected Monthly Costs
- **Light Usage** (1-2 runs/day): ~$3-5/month
- **Heavy Usage** (hourly runs): ~$20-30/month  
- **Development/Testing**: Often within free tier

## 🛡️ Security Best Practices

### API Key Security
1. **Never commit API keys to version control**
   ```bash
   # Add to .gitignore
   echo "*.env" >> .gitignore
   echo ".env.*" >> .gitignore
   ```

2. **Use environment variables only**
   ```bash
   # ✅ Good
   export GOOGLE_API_KEY="your-key"
   
   # ❌ Bad - hardcoded in script
   api_key = "AIza..."
   ```

3. **Restrict API key usage**
   - IP address restrictions
   - API-specific restrictions
   - Regular key rotation

### Monitoring and Alerts
1. **Enable API usage monitoring**
   - Google Cloud Console → APIs & Services → Dashboard
   - Monitor daily/monthly usage

2. **Set up quota alerts**
   - Prevent unexpected charges
   - Get notified before limits

## 🔍 Troubleshooting

### Common Issues

**"API key not valid"**
- Check if APIs are enabled (Places API, Geocoding API)
- Verify API key restrictions
- Wait 5-10 minutes after creating/modifying key

**"REQUEST_DENIED"**  
- Billing not enabled
- API not enabled for this project
- IP restrictions blocking your server

**"OVER_QUERY_LIMIT"**
- Daily quota exceeded
- Billing issue (payment method failed)
- Need to increase quotas

**"ZERO_RESULTS"**
- Search query too specific
- Business not in Google's database
- Try broader search terms

### Debug Steps
1. **Check API key format**
   ```bash
   echo $GOOGLE_API_KEY | wc -c  # Should be ~40 characters
   ```

2. **Test with curl**
   ```bash
   curl "https://maps.googleapis.com/maps/api/geocode/json?address=Kansas+City&key=$GOOGLE_API_KEY"
   ```

3. **Check Google Cloud Console**
   - APIs & Services → Credentials
   - APIs & Services → Dashboard (usage stats)
   - Billing → Overview

## 🔗 Useful Links

- [Google Places API Documentation](https://developers.google.com/maps/documentation/places/web-service/overview)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Places API Pricing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)
- [API Key Best Practices](https://developers.google.com/maps/api-key-best-practices)

## 🎉 Next Steps

Once your Google Places API is set up:

1. **Test the integration**
   ```bash
   python3 test_google_places.py
   ```

2. **Monitor usage for first week**
   - Check Google Cloud Console daily
   - Verify costs are as expected

3. **Implement in KC New Restaurants**
   - Add place details enrichment
   - Enhance email reports with ratings/photos
   - Add geographic analysis features

4. **Set up monitoring**
   - Budget alerts
   - Usage quotas
   - Error notifications

---

**Questions or Issues?** Check the [GitHub Issues](https://github.com/mcollard0/KC-New-Restaurants/issues) or create a new issue for support.

# Google Places API Setup Guide

This guide walks you through setting up Google Places API for the KC New Restaurants project to enable restaurant data enrichment and AI-powered rating predictions.

## Overview

Google Places API provides detailed information about restaurants including:
- Ratings and review counts
- Price levels and cuisine types  
- Amenities (outdoor seating, takeout, delivery, etc.)
- Business hours and location coordinates
- Customer review summaries

**Cost**: Google provides $200 free credit monthly (~40,000 API requests)

## Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project**
   - Click "Select a project" dropdown at the top
   - Click "New Project"
   - Project name: `kc-restaurants-places` (or your preferred name)
   - Leave organization blank (or select if you have one)
   - Click "Create"

3. **Select Your New Project**
   - Ensure the new project is selected in the project dropdown

## Step 2: Enable Places API

1. **Navigate to APIs & Services**
   - From the main menu (☰), go to "APIs & Services" → "Library"

2. **Search for Places API**
   - In the search box, type "Places API"
   - Click on "Places API" from the results

3. **Enable the API**
   - Click the "Enable" button
   - Wait for it to be enabled (usually takes a few seconds)

## Step 3: Create API Credentials

1. **Go to Credentials**
   - From "APIs & Services", click "Credentials" in the left sidebar

2. **Create API Key**
   - Click "Create Credentials" → "API key"
   - A new API key will be generated
   - **Important**: Copy this key immediately and store it securely

3. **Restrict the API Key (Recommended)**
   - Click on the API key you just created
   - Under "API restrictions":
     - Select "Restrict key"
     - Check "Places API"
   - Under "Application restrictions" (choose one):
     - **IP addresses**: Add your server's IP address
     - **HTTP referrers**: Add your domain (for web apps)
     - **None**: Less secure but simpler for development
   - Click "Save"

## Step 4: Set Up Billing (Required for Production)

1. **Navigate to Billing**
   - From the main menu, go to "Billing"
   - If you don't have a billing account, click "Create Account"

2. **Create Billing Account**
   - Follow the prompts to add your payment method
   - **Note**: You won't be charged unless you exceed the $200 monthly credit

3. **Link Project to Billing Account**
   - Ensure your project is linked to the billing account
   - Google provides $200/month free usage (~40,000 requests)

## Step 5: Configure Environment Variables

### For Development (Local Machine)

Create a `.env` file in your project root:

```bash
# .env file
GOOGLE_PLACES_API_KEY=your_api_key_here
GOOGLE_PLACES_REGION=us
```

### For Production (Server)

Add to your shell profile or system environment:

```bash
# Add to ~/.bashrc, ~/.profile, or system environment
export GOOGLE_PLACES_API_KEY="your_api_key_here"
export GOOGLE_PLACES_REGION="us"
```

### For Docker/Containers

Add to your Dockerfile or docker-compose.yml:

```dockerfile
# Dockerfile
ENV GOOGLE_PLACES_API_KEY=your_api_key_here
ENV GOOGLE_PLACES_REGION=us
```

```yaml
# docker-compose.yml
services:
  kc-restaurants:
    environment:
      - GOOGLE_PLACES_API_KEY=your_api_key_here
      - GOOGLE_PLACES_REGION=us
```

## Step 6: Test Your Setup

### Install Dependencies

```bash
pip install googlemaps
```

### Basic Test Script

Create a test file `test_places_api.py`:

```python
#!/usr/bin/env python3

import os
from services.google_places import GooglePlacesService

def test_places_api():
    # Test API connection
    try:
        service = GooglePlacesService()
        
        # Test with a known Kansas City restaurant
        test_data = service.enrich_restaurant_data(
            "Joe's Kansas City Bar-B-Que",
            "3002 W 47th Ave, Kansas City, KS"
        )
        
        if test_data:
            print("✅ Google Places API is working!")
            print(f"   Found: {test_data.name}")
            print(f"   Rating: {test_data.rating}")
            print(f"   Cuisine: {test_data.cuisine_type}")
            print(f"   Price Level: {test_data.price_level}")
            return True
        else:
            print("❌ No data returned from API")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Places API: {e}")
        return False

if __name__ == "__main__":
    test_places_api()
```

### Run the Test

```bash
python test_places_api.py
```

Expected output:
```
✅ Google Places API is working!
   Found: Joe's Kansas City Bar-B-Que
   Rating: 4.3
   Cuisine: BBQ
   Price Level: 2
```

## Step 7: Monitor Usage and Costs

### Check API Usage

1. **Go to APIs & Services → Dashboard**
   - View your API usage statistics
   - Monitor requests per day

2. **Set Up Quotas (Optional)**
   - Go to "APIs & Services" → "Quotas"
   - Find "Places API"
   - Set daily request limits to stay within budget

### Cost Monitoring

1. **Set Up Billing Alerts**
   - Go to "Billing" → "Budgets & alerts"
   - Create a budget alert for your desired spending limit
   - Set alerts at 50%, 90%, and 100% of budget

2. **Current Pricing** (as of 2024):
   - Basic Data (place_id, name, address): $17/1000 requests
   - Contact Data (phone, website): $3/1000 requests  
   - Atmosphere Data (rating, reviews): $5/1000 requests
   - **Free Tier**: First $200/month is free

## Step 8: Security Best Practices

### API Key Security

1. **Never commit API keys to version control**
   - Add `.env` to your `.gitignore`
   - Use environment variables in production

2. **Rotate keys regularly**
   - Create new keys quarterly
   - Delete old keys after rotation

3. **Use API restrictions**
   - Restrict by IP address for server applications
   - Restrict by HTTP referrer for web applications
   - Restrict to only necessary APIs

### Rate Limiting

The Places API has rate limits:
- **100 requests per second** per project
- **Daily quotas** based on your billing account

Our service includes automatic rate limiting and exponential backoff.

## Troubleshooting

### Common Issues

1. **"API key not found" error**
   - Verify environment variable is set correctly
   - Check for extra spaces or quotes in the key

2. **"Places API is not enabled"**
   - Go to APIs & Services → Library
   - Search for "Places API" and ensure it's enabled

3. **"Billing must be enabled"**
   - Set up billing in Google Cloud Console
   - Even free usage requires a billing account

4. **"REQUEST_DENIED" errors**
   - Check API key restrictions
   - Verify the key has access to Places API
   - Ensure billing is enabled

5. **Rate limit exceeded**
   - Our service includes automatic retry with exponential backoff
   - Consider increasing quotas if needed

### Getting Help

- **Google Cloud Support**: https://cloud.google.com/support
- **Places API Documentation**: https://developers.google.com/maps/documentation/places/web-service
- **Pricing Calculator**: https://cloud.google.com/products/calculator

## Integration with KC Restaurants Project

Once your API key is configured, the system will automatically:

1. **Enrich new restaurants** detected from KC business licenses
2. **Update existing restaurants** periodically with fresh Google Places data
3. **Train AI models** using the enriched data
4. **Generate email alerts** with AI-predicted ratings and grades

### Monitoring Integration

Check the application logs for Google Places API activity:

```bash
tail -f kc_new_restaurants.log | grep "Google Places"
```

Expected log entries:
```
2024-12-19 10:30:15 - INFO - Google Places service initialized with region: us
2024-12-19 10:30:16 - INFO - Enriching data for restaurant: Joe's BBQ at 123 Main St
2024-12-19 10:30:17 - INFO - Successfully enriched data for Joe's BBQ
```

---

## Summary Checklist

- [ ] Google Cloud project created
- [ ] Places API enabled
- [ ] API key created and restricted
- [ ] Billing account set up (even for free tier)
- [ ] Environment variables configured
- [ ] Dependencies installed (`googlemaps`)
- [ ] API test successful
- [ ] Usage monitoring set up
- [ ] Security best practices implemented

**Next Steps**: Run the main application with `--dry-run` mode to test Google Places integration without making database changes.

```bash
python3 "KC New Restaurants.py" --dry-run --nodelay
```
