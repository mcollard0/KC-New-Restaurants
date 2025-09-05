#!/usr/bin/env python3
"""
Google Places API Test Script

Tests the Google Places API integration for KC New Restaurants.
Verifies API key setup and basic functionality.

Usage:
    python3 test_google_places.py
"""

import os
import requests
import json
from typing import Dict, Any, Optional

class GooglePlacesAPITest:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.base_url = "https://maps.googleapis.com/maps/api/place"
    
    def _get_api_key(self) -> Optional[str]:
        """Get Google Places API key from environment variables."""
        api_key = os.getenv('GOOGLE_PLACES_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ Error: No Google Places API key found!")
            print("Set one of these environment variables:")
            print("  export GOOGLE_PLACES_API_KEY='your-api-key'")
            print("  export GOOGLE_API_KEY='your-api-key'")
            return None
        return api_key
    
    def test_api_key_validity(self) -> bool:
        """Test if the API key is valid by making a simple request."""
        if not self.api_key:
            return False
        
        print("🔑 Testing API key validity...")
        
        # Use a simple geocoding request to test the key
        url = f"https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': 'Kansas City, MO',
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'OK':
                print("✅ API key is valid and working!")
                return True
            elif data.get('status') == 'REQUEST_DENIED':
                print(f"❌ API key denied: {data.get('error_message', 'Unknown error')}")
                return False
            else:
                print(f"❌ API request failed: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            return False
    
    def test_places_search(self) -> bool:
        """Test Places API search functionality."""
        if not self.api_key:
            return False
        
        print("🔍 Testing Places API search...")
        
        # Search for restaurants in Kansas City
        url = f"{self.base_url}/textsearch/json"
        params = {
            'query': 'restaurants in Kansas City MO',
            'key': self.api_key,
            'type': 'restaurant',
            'location': '39.0997,-94.5786',  # Kansas City coordinates
            'radius': '10000'  # 10km radius
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'OK':
                results = data.get('results', [])
                print(f"✅ Places search successful! Found {len(results)} restaurants")
                
                # Show first few results
                if results:
                    print("\n📍 Sample results:")
                    for i, place in enumerate(results[:3]):
                        name = place.get('name', 'Unknown')
                        address = place.get('formatted_address', 'No address')
                        rating = place.get('rating', 'No rating')
                        print(f"  {i+1}. {name}")
                        print(f"     Address: {address}")
                        print(f"     Rating: {rating}")
                        print()
                
                return True
            else:
                status = data.get('status', 'UNKNOWN')
                error_msg = data.get('error_message', 'No error message')
                print(f"❌ Places search failed: {status} - {error_msg}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error during places search: {e}")
            return False
    
    def test_place_details(self) -> bool:
        """Test Places API details functionality."""
        if not self.api_key:
            return False
        
        print("📋 Testing Places API details...")
        
        # First, get a place ID from a search
        search_url = f"{self.base_url}/textsearch/json"
        search_params = {
            'query': 'Joe\'s Kansas City Bar-B-Que',
            'key': self.api_key
        }
        
        try:
            response = requests.get(search_url, params=search_params, timeout=10)
            data = response.json()
            
            if response.status_code != 200 or data.get('status') != 'OK':
                print("❌ Could not find a test restaurant for details test")
                return False
            
            results = data.get('results', [])
            if not results:
                print("❌ No results found for details test")
                return False
            
            place_id = results[0].get('place_id')
            if not place_id:
                print("❌ No place_id found in results")
                return False
            
            # Now test place details
            details_url = f"{self.base_url}/details/json"
            details_params = {
                'place_id': place_id,
                'key': self.api_key,
                'fields': 'name,formatted_address,rating,formatted_phone_number,website,opening_hours'
            }
            
            response = requests.get(details_url, params=details_params, timeout=10)
            details_data = response.json()
            
            if response.status_code == 200 and details_data.get('status') == 'OK':
                result = details_data.get('result', {})
                name = result.get('name', 'Unknown')
                print(f"✅ Place details successful for: {name}")
                
                # Show details
                print(f"  Address: {result.get('formatted_address', 'N/A')}")
                print(f"  Phone: {result.get('formatted_phone_number', 'N/A')}")
                print(f"  Website: {result.get('website', 'N/A')}")
                print(f"  Rating: {result.get('rating', 'N/A')}")
                
                return True
            else:
                status = details_data.get('status', 'UNKNOWN')
                error_msg = details_data.get('error_message', 'No error message')
                print(f"❌ Place details failed: {status} - {error_msg}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error during place details: {e}")
            return False
    
    def show_usage_info(self):
        """Show API usage and billing information."""
        print("💰 Google Places API Usage Information:")
        print("  • Text Search: $32 per 1,000 requests")
        print("  • Place Details: $17 per 1,000 requests")
        print("  • Geocoding: $5 per 1,000 requests")
        print("  • Monthly free tier: $200 credit (~6,250 text searches)")
        print("  • For KC monitoring: ~30 searches/day = ~$1/month")
        print()
        print("💡 Cost Optimization Tips:")
        print("  • Cache results to avoid duplicate API calls")
        print("  • Use specific field parameters in Place Details")
        print("  • Implement request rate limiting")
        print("  • Monitor usage in Google Cloud Console")

def main():
    print("🚀 Google Places API Test for KC New Restaurants")
    print("=" * 50)
    
    tester = GooglePlacesAPITest()
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if tester.test_api_key_validity():
        tests_passed += 1
    
    if tester.test_places_search():
        tests_passed += 1
    
    if tester.test_place_details():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Google Places API is ready to use.")
    elif tests_passed > 0:
        print("⚠️  Some tests passed. Check the errors above.")
    else:
        print("❌ All tests failed. Check your API key and billing setup.")
    
    print()
    tester.show_usage_info()
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
