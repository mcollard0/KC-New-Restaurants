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
