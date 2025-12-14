# Enable Google Places API (New) - Required!

## Current Status
❌ **Places API (New) is NOT enabled** - The application is using mock data instead of real Google Places data.

## What's Happening
The application is getting **403 Forbidden** errors when calling the new Places API, which means:
- Your API key is valid
- But the "Places API (New)" service is not enabled in your Google Cloud project

## Fix This Now

### Step 1: Enable Places API (New)
Go to: **https://console.cloud.google.com/apis/library/places-backend.googleapis.com**

1. Select your Google Cloud project
2. Click **"ENABLE"** button
3. Wait 1-2 minutes for propagation

### Step 2: Verify API is Enabled
Go to: **https://console.cloud.google.com/apis/dashboard**

You should see "Places API (New)" in your enabled APIs list.

### Step 3: Check API Key Restrictions
Go to: **https://console.cloud.google.com/apis/credentials**

1. Click on your API key
2. Under "API restrictions":
   - Either select "Don't restrict key" (for testing)
   - OR select "Restrict key" and add:
     - ✅ **Places API (New)**
     
**Important**: Make sure it says "Places API (New)" NOT just "Places API" (the old one)

### Step 4: Test
After enabling, wait 2 minutes then test:

```bash
conda activate kc-restaurants
python "KC New Restaurants.py" --dry-run --nodelay
```

Look for:
- ✅ "Successfully enriched data for [restaurant name]"
- ✅ Real ratings and reviews (not mock data)
- ❌ NO "Places API (New) not enabled" warnings

## Differences Between APIs

### Old "Places API" (deprecated)
- Endpoint: `https://maps.googleapis.com/maps/api/place/`
- **NOT what we're using**

### New "Places API (New)" (v1)
- Endpoint: `https://places.googleapis.com/v1/`
- **This is what the application uses**
- **MUST be enabled separately**

## Current Behavior (Mock Data)
Right now the application is using fake data:
- Mock place IDs like `mock_7458150f306e58b4`
- Random ratings
- No real reviews
- No real amenities

This defeats the purpose of the enrichment!

## Cost After Enabling
With $200/month Google Cloud free credit:
- Text Search: $32 per 1,000 requests
- Place Details: $17 per 1,000 requests
- **Estimated cost: $3-5/month** (well under free credit limit)

## After You Enable It
The application will retrieve real data:
- ✅ Actual Google ratings (1-5 stars)
- ✅ Review counts
- ✅ Price levels ($ to $$$$)
- ✅ Amenities (outdoor seating, takeout, etc.)
- ✅ Business hours
- ✅ Cuisine types
- ✅ AI predictions based on real data

Enable it now: **https://console.cloud.google.com/apis/library/places-backend.googleapis.com**
