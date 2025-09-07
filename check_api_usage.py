#!/usr/bin/env python3
"""
Script to check Google Places API usage and estimate costs based on recent runs
"""

import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)));

try:
    from services.google_places_client import GooglePlacesClient
    
    # Suppress INFO logs for cleaner output
    logging.getLogger().setLevel(logging.WARNING)
    
    print("🔍 Google Places API Usage Analysis")
    print("=" * 50)
    
    # Initialize client to check usage
    client = GooglePlacesClient()
    
    # Get usage summary
    usage = client.get_quota_usage()
    
    print(f"📊 Current Session Usage:")
    print(f"   Total API calls: {usage['total_calls']:,}")
    print(f"   - Text searches: {usage['text_search_calls']:,}")
    print(f"   - Place details: {usage['place_details_calls']:,}")
    print(f"   - Geocoding: {usage['geocoding_calls']:,}")
    print(f"   Estimated cost: ${usage['estimated_cost_usd']:.4f}")
    
    if 'error_summary' in usage:
        print(f"   Errors: {usage['error_summary']}")
    
    print()
    print("💰 Google Places API Pricing (2024 rates):")
    print(f"   - Text Search: $32.00 per 1,000 requests")
    print(f"   - Place Details: $17.00 per 1,000 requests")
    print(f"   - Geocoding: $5.00 per 1,000 requests")
    
    print()
    print("📈 Estimated Usage Based on Recent Runs:")
    print("   From recent log analysis:")
    
    # Based on the logs we've seen
    recent_runs = [
        {"date": "2025-09-07 (Run 1)", "enriched": 351, "failed": 28},
        {"date": "2025-09-07 (Run 2)", "enriched": 350, "failed": 29},
        {"date": "2025-09-07 (Run 3)", "enriched": 350, "failed": 29}
    ]
    
    total_enriched = 0
    total_failed = 0
    
    for run in recent_runs:
        enriched = run["enriched"]
        failed = run["failed"]
        total_enriched += enriched
        total_failed += failed
        
        # Each successful enrichment = 1 text search + 1 place details
        # Each failed enrichment = 1 text search only
        text_searches = enriched + failed
        place_details = enriched
        
        cost = (text_searches / 1000.0 * 32.0) + (place_details / 1000.0 * 17.0)
        
        print(f"   {run['date']}: {text_searches} text searches + {place_details} place details = ${cost:.2f}")
    
    # Calculate totals
    total_text_searches = total_enriched + total_failed
    total_place_details = total_enriched
    total_estimated_cost = (total_text_searches / 1000.0 * 32.0) + (total_place_details / 1000.0 * 17.0)
    
    print()
    print("🎯 Total Estimated Usage for Recent Runs:")
    print(f"   Text searches: {total_text_searches:,}")
    print(f"   Place details: {total_place_details:,}")
    print(f"   Total estimated cost: ${total_estimated_cost:.2f}")
    
    print()
    print("⚠️  Cost Analysis:")
    if total_estimated_cost > 50:
        print(f"   🚨 HIGH USAGE: ${total_estimated_cost:.2f} estimated from recent runs")
        print(f"   💡 Consider implementing:")
        print(f"      - Caching to avoid re-enriching existing restaurants")
        print(f"      - Batch processing instead of full runs")
        print(f"      - Rate limiting to spread costs over time")
    elif total_estimated_cost > 20:
        print(f"   ⚠️  MODERATE USAGE: ${total_estimated_cost:.2f} estimated from recent runs")
        print(f"   💡 Consider implementing caching for repeat runs")
    else:
        print(f"   ✅ LOW USAGE: ${total_estimated_cost:.2f} estimated from recent runs")
    
    print()
    print("📝 Notes:")
    print("   - These are estimates based on visible log data")
    print("   - Actual costs may vary based on all API usage")
    print("   - Check Google Cloud Console for exact billing")
    print("   - Current session usage only shows this run's calls")
    
except Exception as e:
    print(f"Error checking API usage: {e}")
    sys.exit(1)
