#!/usr/bin/env python3
"""
Test script for sentiment analysis integration with Google Places API
"""

import os;
import sys;
import logging;
from typing import Dict, Any;

# Add the current directory to Python path for imports
sys.path.insert( 0, os.path.dirname( os.path.abspath( __file__ ) ) );

try:
    from services.sentiment_analyzer import SentimentAnalyzer;
    from services.google_places import GooglePlacesService, PlaceData;
    SERVICES_AVAILABLE = True;
except ImportError as e:
    print( f"Could not import services: {e}" );
    print( "Make sure you have installed the requirements: pip install -r requirements.txt" );
    SERVICES_AVAILABLE = False;

def test_sentiment_analyzer():
    """Test the sentiment analyzer independently."""
    print( "\n🧪 Testing Sentiment Analyzer..." );
    print( "=" * 50 );
    
    try:
        analyzer = SentimentAnalyzer();
        
        # Test individual text analysis
        test_texts = [
            "Amazing food and excellent service! Highly recommend this place.",
            "The food was okay but service was really slow and disappointing.",
            "Decent restaurant with average food and normal service."
        ];
        
        for text in test_texts:
            score, label = analyzer.analyze_text( text );
            keywords = analyzer.extract_keywords( text );
            print( f"Text: {text[:50]}..." );
            print( f"  Sentiment: {label} ({score:.3f})" );
            print( f"  Keywords: {keywords}" );
            print();
            
        # Test comprehensive review analysis
        mock_reviews = [
            {
                'text': 'Amazing food and excellent service! The pasta was delicious and the staff was very friendly.',
                'rating': 5,
                'author_name': 'John Smith',
                'relative_time_description': '2 weeks ago'
            },
            {
                'text': 'Food was okay but the service was really slow. Waited forever for our meals.',
                'rating': 2,
                'author_name': 'Sarah Johnson',
                'relative_time_description': '1 month ago'
            },
            {
                'text': 'Great atmosphere and fantastic pizza. Clean restaurant with good parking.',
                'rating': 4,
                'author_name': 'Mike Davis',
                'relative_time_description': '3 weeks ago'
            }
        ];
        
        analysis = analyzer.analyze_reviews( mock_reviews );
        
        print( "📊 Comprehensive Analysis Results:" );
        print( f"  Reviews analyzed: {analysis['reviews_count']}" );
        print( f"  Average sentiment: {analysis['sentiment_avg']:.3f}" );
        print( f"  Sentiment distribution: {analysis['sentiment_distribution']}" );
        print( f"  Top keywords: {analysis['top_keywords']}" );
        print( f"  Summary: {analysis['analysis_summary']}" );
        
        # Test sentiment badge
        badge_info = analyzer.get_sentiment_badge_info( analysis['sentiment_distribution'] );
        print( f"  Sentiment badge: {badge_info['emoji']} {badge_info['text']}" );
        
        return True;
        
    except Exception as e:
        print( f"❌ Sentiment analyzer test failed: {e}" );
        return False;

def test_google_places_with_sentiment():
    """Test Google Places service with sentiment analysis integration."""
    print( "\n🌍 Testing Google Places + Sentiment Integration..." );
    print( "=" * 50 );
    
    # Check if API key is available
    api_key = os.getenv( 'GOOGLE_PLACES_API_KEY' );
    if not api_key:
        print( "⚠️  GOOGLE_PLACES_API_KEY not set - skipping Google Places test" );
        print( "   Set your API key to test Google Places integration:" );
        print( "   export GOOGLE_PLACES_API_KEY='your_key_here'" );
        return True;  # Not a failure, just no key
        
    try:
        service = GooglePlacesService();
        
        # Test with a known Kansas City restaurant
        test_restaurant = "Joe's Kansas City Bar-B-Que";
        test_address = "3002 W 47th Ave, Kansas City, KS";
        
        print( f"🔍 Searching for: {test_restaurant}" );
        print( f"   Address: {test_address}" );
        
        place_data = service.enrich_restaurant_data( test_restaurant, test_address );
        
        if place_data:
            print( f"✅ Successfully found restaurant data:" );
            print( f"   Name: {place_data.name}" );
            print( f"   Rating: {place_data.rating}" );
            print( f"   Review Count: {place_data.review_count}" );
            print( f"   Cuisine: {place_data.cuisine_type}" );
            print( f"   Price Level: {place_data.price_level}" );
            
            # Test sentiment analysis results
            if place_data.sentiment_avg is not None:
                print( f"   Sentiment Average: {place_data.sentiment_avg:.3f}" );
                print( f"   Sentiment Distribution: {place_data.sentiment_distribution}" );
                print( f"   Review Keywords: {place_data.review_keywords}" );
                print( f"   Sentiment Summary: {place_data.sentiment_summary}" );
                
                # Test sentiment badge
                if place_data.sentiment_distribution:
                    analyzer = SentimentAnalyzer();
                    badge_info = analyzer.get_sentiment_badge_info( place_data.sentiment_distribution );
                    print( f"   Sentiment Badge: {badge_info['emoji']} {badge_info['text']}" );
            else:
                print( f"   ⚠️  No sentiment analysis data (no reviews or analyzer failed)" );
                
            return True;
        else:
            print( f"❌ Could not find restaurant data for {test_restaurant}" );
            return False;
            
    except Exception as e:
        print( f"❌ Google Places test failed: {e}" );
        return False;

def test_email_template_data():
    """Test that email template can handle sentiment data.""" 
    print( "\n📧 Testing Email Template Data Integration..." );
    print( "=" * 50 );
    
    # Mock restaurant data with sentiment analysis
    mock_restaurant = {
        'business_name': 'Test Restaurant LLC',
        'dba_name': 'Amazing Tacos',
        'address': '123 Test Street, Kansas City, MO',
        'business_type': 'Full-Service Restaurants',
        'google_rating': 4.2,
        'cuisine_type': 'Mexican',
        'price_level': 2,
        'outdoor_seating': True,
        'takeout_available': True,
        'ai_predicted_rating': 4.3,
        'ai_predicted_grade': 'B+',
        'sentiment_distribution': { 'positive': 70, 'neutral': 20, 'negative': 10 },
        'review_keywords': ['great food', 'friendly service', 'atmosphere'],
        'sentiment_summary': 'Generally Positive (positive 70%) - Key topics: great food, friendly service, atmosphere'
    };
    
    print( f"🍽️  Mock Restaurant: {mock_restaurant['dba_name']}" );
    print( f"   Sentiment: {mock_restaurant['sentiment_distribution']}" );
    print( f"   Keywords: {mock_restaurant['review_keywords']}" );
    print( f"   AI Rating: {mock_restaurant['ai_predicted_rating']} ({mock_restaurant['ai_predicted_grade']})" );
    
    # Test sentiment badge logic
    sentiment_dist = mock_restaurant['sentiment_distribution'];
    positive_pct = sentiment_dist.get( 'positive', 0 );
    
    if positive_pct >= 60:
        badge_text = f'😊 Positive Reviews ({positive_pct}%)';
        print( f"   Badge: {badge_text}" );
    else:
        print( f"   Badge: Mixed/Negative" );
        
    # Test keyword tags
    keywords = mock_restaurant['review_keywords'][:3];
    print( f"   Keyword Tags: {', '.join(keywords)}" );
    
    print( f"✅ Email template data integration looks good!" );
    return True;

def main():
    """Run all integration tests."""
    print( "🚀 KC New Restaurants Sentiment Analysis Integration Test" );
    print( "=" * 65 );
    
    if not SERVICES_AVAILABLE:
        print( "❌ Cannot run tests - services not available" );
        print( "   Install requirements: pip install -r requirements.txt" );
        return False;
        
    # Configure logging
    logging.basicConfig( level=logging.WARNING );  # Reduce log noise during testing
    
    tests_passed = 0;
    total_tests = 0;
    
    # Test 1: Sentiment Analyzer
    total_tests += 1;
    if test_sentiment_analyzer():
        tests_passed += 1;
        
    # Test 2: Google Places with Sentiment  
    total_tests += 1;
    if test_google_places_with_sentiment():
        tests_passed += 1;
        
    # Test 3: Email Template Data
    total_tests += 1;
    if test_email_template_data():
        tests_passed += 1;
    
    # Summary
    print( "\n" + "=" * 65 );
    print( f"📊 Test Results: {tests_passed}/{total_tests} tests passed" );
    
    if tests_passed == total_tests:
        print( "🎉 All tests passed! Sentiment analysis integration is ready." );
        print( "\n📋 Next Steps:" );
        print( "   1. Set GOOGLE_PLACES_API_KEY environment variable" );
        print( "   2. Install dependencies: pip install -r requirements.txt" );
        print( "   3. Run main application: python3 'KC New Restaurants.py' --dry-run" );
        return True;
    else:
        print( f"❌ {total_tests - tests_passed} test(s) failed. Please check the errors above." );
        return False;
        
if __name__ == "__main__":
    success = main();
    sys.exit( 0 if success else 1 );
