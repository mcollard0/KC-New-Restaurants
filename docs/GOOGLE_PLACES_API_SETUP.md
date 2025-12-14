# Google Places API Setup

## Current Status
❌ **API Key Invalid** - The API key needs to be properly configured for Places API (New)

## Required Steps

### 1. Enable Places API (New)
The application uses the **new Places API v1** (not the legacy Places API).

**Enable at**: https://console.cloud.google.com/apis/library/places-backend.googleapis.com

Or search for "Places API (New)" in Google Cloud Console → APIs & Services → Library

### 2. Create/Update API Key

1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new API key or edit existing one
3. **Restrict the API key** to only:
   - Places API (New)
   
4. **Important**: The key must be enabled for:
   - `places.googleapis.com` service
   - Text Search (new)
   - Place Details (new)

### 3. Set Environment Variable

The current API key in the conda environment is only **25 characters**, which seems too short.

Google API keys are typically **39 characters** long and start with `AIza`.

**Update the key**:
```bash
# Set in conda environment
conda env config vars set GOOGLE_PLACES_API_KEY="YOUR_ACTUAL_39_CHAR_KEY" -n kc-restaurants

# Or set system-wide in ~/.bashrc
export GOOGLE_PLACES_API_KEY="YOUR_ACTUAL_39_CHAR_KEY"
```

Then reactivate the environment:
```bash
conda deactivate
conda activate kc-restaurants
```

### 4. Verify Setup

Test the API key:
```bash
source /home/michael/anaconda3/etc/profile.d/conda.sh
conda activate kc-restaurants

python << 'EOF'
import os;
import requests;

api_key = os.getenv( 'GOOGLE_PLACES_API_KEY' );
print( f"API Key length: {len(api_key)} chars" );
print( f"API Key starts with 'AIza': {api_key.startswith('AIza') if api_key else False}" );

# Test the API
headers = {
    'Content-Type': 'application/json',
    'X-Goog-Api-Key': api_key,
    'X-Goog-FieldMask': 'places.id,places.displayName'
};

search_data = {
    "textQuery": "McDonald's Kansas City Missouri",
    "maxResultCount": 1
};

response = requests.post(
    "https://places.googleapis.com/v1/places:searchText",
    headers=headers,
    json=search_data
);

print( f"\nAPI Test Status: {response.status_code}" );
if response.status_code == 200:
    print( "✅ API key is valid!" );
else:
    print( f"❌ API Error: {response.json()}" );
EOF
```

## API Implementation Details

The application uses:
- **Endpoint**: `https://places.googleapis.com/v1`
- **Methods**:
  - Text Search: `POST /places:searchText`
  - Place Details: `GET /places/{place_id}`
- **Authentication**: `X-Goog-Api-Key` header
- **Field Masks**: `X-Goog-FieldMask` header for requested fields

## Pricing (as of 2024)

With $200/month free credit:
- Text Search: $32 per 1,000 requests
- Place Details: $17 per 1,000 requests
- Estimated monthly cost: $3-5 for typical usage (~40,000 requests)

## Troubleshooting

### Error: "API key not valid"
- Verify key is enabled for "Places API (New)" not legacy "Places API"
- Check key restrictions allow `places.googleapis.com`
- Ensure key length is 39 characters

### Error: 403 Forbidden
- Enable "Places API (New)" in Google Cloud Console
- Wait 1-2 minutes for API enablement to propagate

### Error: 429 Too Many Requests
- Rate limiting is set to 8 req/s (configurable)
- Increase delays in `google_places_client.py` if needed
