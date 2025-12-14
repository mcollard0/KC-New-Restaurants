# Fix API Key IP Restriction

## The Problem
Your API key has IP address restrictions enabled, and your current IP is blocked:
- **Your IP**: `2605:a601:adad:2300:a61:f511:9aaa:4653` (IPv6)
- **Error**: "The provided API key has an IP address restriction"

## Solution: Remove IP Restrictions (Recommended for Development)

### Quick Fix (5 minutes)
1. Go to: **https://console.cloud.google.com/apis/credentials**
2. Click on your API key
3. Scroll to **"Application restrictions"**
4. Select **"None"** (instead of "IP addresses")
5. Click **"Save"**
6. Wait 1-2 minutes for propagation

### Alternative: Add Your IP Address
If you need IP restrictions for security:

1. Go to: **https://console.cloud.google.com/apis/credentials**
2. Click on your API key  
3. Under **"Application restrictions"** → **"IP addresses"**
4. Add your IPv6 address: `2605:a601:adad:2300:a61:f511:9aaa:4653/128`
5. Also add your IPv4 if you have one (run: `curl -4 ifconfig.me`)
6. Click **"Save"**

**Note**: If your IP changes (dynamic IP), you'll need to update this frequently.

## Test After Fixing

Run this to verify:

```bash
python3 << 'EOF'
import os, requests;

api_key = os.getenv( 'GOOGLE_PLACES_API_KEY' );
response = requests.post(
    "https://places.googleapis.com/v1/places:searchText",
    headers={
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.id,places.displayName,places.rating'
    },
    json={"textQuery": "McDonald's Kansas City Missouri", "maxResultCount": 1}
);

print( f"Status: {response.status_code}" );
if response.status_code == 200:
    print( "✅ API is working! IP restriction fixed!" );
    place = response.json()['places'][0];
    print( f"Restaurant: {place['displayName']['text']}" );
    print( f"Rating: {place.get('rating', 'N/A')}" );
else:
    print( f"❌ Still blocked: {response.json()}" );
EOF
```

## Then Test the Full Application

```bash
conda activate kc-restaurants
python "KC New Restaurants.py" --dry-run --nodelay
```

You should see:
- ✅ Real restaurant names and ratings
- ✅ "Successfully enriched data for..."
- ❌ NO "403 Forbidden" errors
- ❌ NO mock data

## Why This Matters
Without fixing this, the application will **never** get real Google Places data - it will always use fake mock data, which defeats the entire purpose of the enrichment feature!

**Fix it now**: https://console.cloud.google.com/apis/credentials
