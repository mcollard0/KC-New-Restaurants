#!/usr/bin/env python3
"""
Enhanced Google Places Client Module
Robust wrapper for Google Places API with proper error handling, rate limiting, and quota tracking
"""

import os;
import sys;
import logging;
import time;
import re;
from typing import Dict, List, Optional, Any, Tuple;
from dataclasses import dataclass;
from datetime import datetime;

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

try:
    import googlemaps;
    from googlemaps.exceptions import ApiError, Timeout, TransportError;
    GOOGLEMAPS_AVAILABLE = True;
except ImportError:
    logging.warning( "googlemaps library not available. Install with: pip install googlemaps" );
    GOOGLEMAPS_AVAILABLE = False;

try:
    from utils.retry_utils import robust_api_call, ErrorHandler, ErrorCategory;
    from .sentiment_analyzer import SentimentAnalyzer;
    UTILS_AVAILABLE = True;
except ImportError as e:
    logging.warning( f"Utils not available: {e}" );
    UTILS_AVAILABLE = False;

logger = logging.getLogger( __name__ );

@dataclass
class PlaceData:
    """Enhanced structured representation of Google Places data."""
    # Basic identifiers
    place_id: Optional[str] = None;
    name: Optional[str] = None;
    formatted_address: Optional[str] = None;
    
    # Ratings and reviews
    rating: Optional[float] = None;
    review_count: Optional[int] = None;
    price_level: Optional[int] = None;
    
    # Location data
    latitude: Optional[float] = None;
    longitude: Optional[float] = None;
    
    # Business information
    cuisine_type: Optional[str] = None;
    business_hours: Optional[Dict] = None;
    
    # Amenities
    outdoor_seating: Optional[bool] = None;
    takeout_available: Optional[bool] = None;
    delivery_available: Optional[bool] = None;
    reservations_accepted: Optional[bool] = None;
    wheelchair_accessible: Optional[bool] = None;
    good_for_children: Optional[bool] = None;
    serves_alcohol: Optional[bool] = None;
    parking_available: Optional[bool] = None;
    
    # Review analysis
    review_summary: Optional[str] = None;
    sentiment_avg: Optional[float] = None;
    sentiment_distribution: Optional[Dict[str, int]] = None;
    review_keywords: Optional[List[str]] = None;
    sentiment_summary: Optional[str] = None;
    
    # Metadata
    last_updated: Optional[str] = None;
    api_fields_retrieved: Optional[List[str]] = None;

@dataclass 
class QuotaTracker:
    """Track API quota usage and costs."""
    text_search_calls: int = 0;
    place_details_calls: int = 0;
    geocoding_calls: int = 0;
    
    # Pricing per 1000 requests (as of 2024)
    text_search_cost_per_1k: float = 32.0;
    place_details_cost_per_1k: float = 17.0;
    geocoding_cost_per_1k: float = 5.0;
    
    def add_text_search( self, count: int = 1 ):
        """Add text search API calls to tracker."""
        self.text_search_calls += count;
        
    def add_place_details( self, count: int = 1 ):
        """Add place details API calls to tracker."""
        self.place_details_calls += count;
        
    def add_geocoding( self, count: int = 1 ):
        """Add geocoding API calls to tracker."""
        self.geocoding_calls += count;
        
    def get_total_calls( self ) -> int:
        """Get total API calls made."""
        return self.text_search_calls + self.place_details_calls + self.geocoding_calls;
        
    def get_estimated_cost( self ) -> float:
        """Calculate estimated cost in USD."""
        text_cost = ( self.text_search_calls / 1000.0 ) * self.text_search_cost_per_1k;
        details_cost = ( self.place_details_calls / 1000.0 ) * self.place_details_cost_per_1k;
        geocoding_cost = ( self.geocoding_calls / 1000.0 ) * self.geocoding_cost_per_1k;
        
        return text_cost + details_cost + geocoding_cost;
        
    def get_usage_summary( self ) -> Dict[str, Any]:
        """Get detailed usage summary."""
        return {
            'total_calls': self.get_total_calls(),
            'text_search_calls': self.text_search_calls,
            'place_details_calls': self.place_details_calls,
            'geocoding_calls': self.geocoding_calls,
            'estimated_cost_usd': round( self.get_estimated_cost(), 4 )
        };

class GooglePlacesClient:
    """Enhanced Google Places API client with robust error handling."""
    
    def __init__( self, 
                 api_key: Optional[str] = None, 
                 region: str = "us",
                 rate_limit_per_second: float = 8.0,
                 enable_sentiment_analysis: bool = True ):
        """
        Initialize Google Places client.
        
        Args:
            api_key: Google Places API key (defaults to GOOGLE_PLACES_API_KEY env var)
            region: Region bias for search results (default: 'us')
            rate_limit_per_second: Rate limit for API calls (default: 8.0 req/s)
            enable_sentiment_analysis: Whether to enable sentiment analysis of reviews
        """
        if not GOOGLEMAPS_AVAILABLE:
            raise ImportError( "googlemaps library is required. Install with: pip install googlemaps" );
            
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv( 'GOOGLE_PLACES_API_KEY' );
        if not self.api_key:
            raise ValueError( "Google Places API key is required. Set GOOGLE_PLACES_API_KEY environment variable or pass api_key parameter." );
            
        self.region = region;
        self.rate_limit = rate_limit_per_second;
        
        # Initialize Google Maps client
        try:
            self.client = googlemaps.Client( key=self.api_key );
        except Exception as e:
            raise ValueError( f"Failed to initialize Google Maps client: {e}" );
            
        # Initialize error handler and quota tracker
        self.error_handler = ErrorHandler( "GooglePlacesClient" ) if UTILS_AVAILABLE else None;
        self.quota_tracker = QuotaTracker();
        
        # Initialize sentiment analyzer if requested
        self.sentiment_analyzer = None;
        if enable_sentiment_analysis:
            try:
                self.sentiment_analyzer = SentimentAnalyzer();
                logger.info( "Sentiment analyzer initialized for review analysis" );
            except Exception as e:
                logger.warning( f"Could not initialize sentiment analyzer: {e}" );
                
        logger.info( f"Google Places client initialized (region: {region}, rate_limit: {rate_limit_per_second} req/s)" );

    def _handle_api_error( self, exception: Exception, context: str = "" ) -> ErrorCategory:
        """Handle and categorize API errors."""
        if self.error_handler:
            return self.error_handler.handle_error( exception, context );
        else:
            # Fallback error handling without utils
            logger.error( f"Google Places API error in {context}: {exception}" );
            return None;

    @robust_api_call( attempts=5, rate_per_second=8.0 ) if UTILS_AVAILABLE else lambda f: f
    def search_place( self, business_name: str, address: str, search_type: str = "restaurant" ) -> Optional[str]:
        """
        Search for a place and return its place_id.
        
        Args:
            business_name: Name of the business to search for
            address: Address of the business
            search_type: Type of place to search for (default: 'restaurant')
            
        Returns:
            Google place_id if found, None otherwise
        """
        if not business_name or not address:
            logger.warning( "Empty business name or address provided for search" );
            return None;
            
        # Construct search query
        query = f"{business_name} {address}".strip();
        logger.debug( f"Searching for place: {query}" );
        
        try:
            # Use Text Search API
            results = self.client.places( query=query, type=search_type, region=self.region );
            self.quota_tracker.add_text_search();
            
            if results.get( 'results' ):
                place_id = results[ 'results' ][ 0 ][ 'place_id' ];
                logger.debug( f"Found place_id: {place_id} for query: {query}" );
                return place_id;
            else:
                logger.info( f"No results found for query: {query}" );
                return None;
                
        except ( ApiError, Timeout, TransportError ) as e:
            self._handle_api_error( e, f"search_place({business_name})" );
            raise;
        except Exception as e:
            self._handle_api_error( e, f"search_place({business_name})" );
            return None;

    @robust_api_call( attempts=3, rate_per_second=8.0 ) if UTILS_AVAILABLE else lambda f: f
    def get_place_details( self, place_id: str, fields: Optional[List[str]] = None ) -> Optional[PlaceData]:
        """
        Get detailed information about a place.
        
        Args:
            place_id: Google place_id
            fields: Specific fields to retrieve (None for default set)
            
        Returns:
            PlaceData object with all available information
        """
        if not place_id:
            logger.warning( "Empty place_id provided" );
            return None;
            
        # Define default fields to retrieve
        if fields is None:
            fields = [
                'place_id', 'name', 'formatted_address', 'geometry',
                'rating', 'user_ratings_total', 'price_level', 'types',
                'opening_hours', 'reviews', 'serves_beer', 'serves_wine', 
                'takeout', 'delivery', 'dine_in', 'reservable',
                'wheelchair_accessible_entrance'
            ];
            
        try:
            result = self.client.place( place_id=place_id, fields=fields );
            self.quota_tracker.add_place_details();
            
            if result.get( 'result' ):
                place_data = self._parse_place_details( result[ 'result' ] );
                place_data.api_fields_retrieved = fields;
                place_data.last_updated = datetime.now().isoformat();
                
                logger.debug( f"Retrieved details for place_id: {place_id}" );
                return place_data;
            else:
                logger.warning( f"No result found for place_id: {place_id}" );
                return None;
                
        except ( ApiError, Timeout, TransportError ) as e:
            self._handle_api_error( e, f"get_place_details({place_id})" );
            raise;
        except Exception as e:
            self._handle_api_error( e, f"get_place_details({place_id})" );
            return None;

    def _parse_place_details( self, place_result: Dict ) -> PlaceData:
        """Parse Google Places API result into structured PlaceData."""
        data = PlaceData();
        
        # Basic information
        data.place_id = place_result.get( 'place_id' );
        data.name = place_result.get( 'name' );
        data.formatted_address = place_result.get( 'formatted_address' );
        
        # Rating and reviews
        data.rating = place_result.get( 'rating' );
        data.review_count = place_result.get( 'user_ratings_total' );
        data.price_level = place_result.get( 'price_level' );
        
        # Location
        geometry = place_result.get( 'geometry', {} );
        location = geometry.get( 'location', {} );
        data.latitude = location.get( 'lat' );
        data.longitude = location.get( 'lng' );
        
        # Cuisine type from place types
        data.cuisine_type = self._determine_cuisine_type( place_result );
        
        # Business hours
        opening_hours = place_result.get( 'opening_hours', {} );
        data.business_hours = self._parse_business_hours( opening_hours );
        
        # Amenities
        data.outdoor_seating = self._infer_outdoor_seating( place_result );
        data.takeout_available = place_result.get( 'takeout' );
        data.delivery_available = place_result.get( 'delivery' );
        data.reservations_accepted = place_result.get( 'reservable' );
        data.wheelchair_accessible = place_result.get( 'wheelchair_accessible_entrance' );
        data.good_for_children = self._infer_child_friendly( place_result );
        data.serves_alcohol = place_result.get( 'serves_beer' ) or place_result.get( 'serves_wine' );
        data.parking_available = self._infer_parking_available( place_result );
        
        # Process reviews with sentiment analysis
        reviews = place_result.get( 'reviews', [] );
        if reviews and self.sentiment_analyzer:
            self._analyze_reviews( data, reviews );
        elif reviews:
            data.review_summary = self._create_basic_review_summary( reviews );
            
        return data;

    def _determine_cuisine_type( self, place_result: Dict ) -> Optional[str]:
        """Determine primary cuisine type from place types and name."""
        types = place_result.get( 'types', [] );
        name = place_result.get( 'name', '' ).lower();
        
        # Map Google types to cuisine categories
        cuisine_mapping = {
            'chinese_restaurant': 'Chinese',
            'italian_restaurant': 'Italian', 
            'mexican_restaurant': 'Mexican',
            'indian_restaurant': 'Indian',
            'thai_restaurant': 'Thai',
            'japanese_restaurant': 'Japanese',
            'korean_restaurant': 'Korean',
            'french_restaurant': 'French',
            'mediterranean_restaurant': 'Mediterranean',
            'greek_restaurant': 'Greek',
            'vietnamese_restaurant': 'Vietnamese',
            'pizza_restaurant': 'Pizza',
            'seafood_restaurant': 'Seafood',
            'steakhouse': 'Steakhouse',
            'barbecue_restaurant': 'BBQ',
            'fast_food_restaurant': 'Fast Food',
            'cafe': 'Cafe',
            'bakery': 'Bakery'
        };
        
        # Check types first
        for place_type in types:
            if place_type in cuisine_mapping:
                return cuisine_mapping[ place_type ];
                
        # Check name for cuisine indicators
        cuisine_keywords = {
            'pizza': 'Pizza',
            'chinese': 'Chinese',
            'mexican': 'Mexican', 
            'italian': 'Italian',
            'thai': 'Thai',
            'indian': 'Indian',
            'sushi': 'Japanese',
            'bbq': 'BBQ',
            'barbecue': 'BBQ',
            'seafood': 'Seafood',
            'steakhouse': 'Steakhouse',
            'cafe': 'Cafe',
            'bakery': 'Bakery'
        };
        
        for keyword, cuisine in cuisine_keywords.items():
            if keyword in name:
                return cuisine;
                
        # Default for restaurants
        if 'restaurant' in types:
            return 'American';
            
        return None;

    def _parse_business_hours( self, opening_hours: Dict ) -> Optional[Dict]:
        """Parse business hours into structured format."""
        if not opening_hours:
            return None;
            
        weekday_text = opening_hours.get( 'weekday_text', [] );
        if not weekday_text:
            return None;
            
        # Parse weekday text into structured format
        hours_dict = {};
        days_map = {
            'monday': 'monday',
            'tuesday': 'tuesday', 
            'wednesday': 'wednesday',
            'thursday': 'thursday',
            'friday': 'friday',
            'saturday': 'saturday',
            'sunday': 'sunday'
        };
        
        for day_text in weekday_text:
            try:
                # Format: "Monday: 11:00 AM – 10:00 PM"
                parts = day_text.split( ':', 1 );
                if len( parts ) == 2:
                    day_name = parts[ 0 ].strip().lower();
                    hours = parts[ 1 ].strip();
                    
                    if day_name in days_map:
                        # Simplify hours format
                        hours = hours.replace( '\u2013', '-' ).replace( '\u2014', '-' );  # Replace em-dash
                        hours = re.sub( r'\s*(AM|PM)', r'\1', hours, flags=re.IGNORECASE );
                        hours_dict[ days_map[ day_name ] ] = hours;
                        
            except Exception as e:
                logger.debug( f"Error parsing business hours '{day_text}': {e}" );
                
        return hours_dict if hours_dict else None;

    def _infer_outdoor_seating( self, place_result: Dict ) -> Optional[bool]:
        """Infer outdoor seating from available data."""
        # This would require additional analysis or specific fields
        # For now, return None (unknown)
        return None;

    def _infer_child_friendly( self, place_result: Dict ) -> Optional[bool]:
        """Infer if establishment is child-friendly."""
        types = place_result.get( 'types', [] );
        name = place_result.get( 'name', '' ).lower();
        
        # Family-friendly indicators
        family_types = [ 'family_restaurant' ];
        family_keywords = [ 'family', 'kids', 'children' ];
        
        if any( t in types for t in family_types ):
            return True;
        if any( keyword in name for keyword in family_keywords ):
            return True;
            
        # Fast food chains are generally child-friendly
        if 'meal_takeaway' in types or 'fast_food_restaurant' in types:
            return True;
            
        return None;  # Unknown

    def _infer_parking_available( self, place_result: Dict ) -> Optional[bool]:
        """Infer parking availability."""
        # This would require additional analysis or specific fields
        # For now, return None (unknown)
        return None;

    def _analyze_reviews( self, place_data: PlaceData, reviews: List[Dict] ):
        """Analyze reviews with sentiment analysis."""
        if not self.sentiment_analyzer or not reviews:
            return;
            
        try:
            # Convert reviews to format expected by sentiment analyzer
            review_data = [];
            for review in reviews[ :5 ]:  # Limit to first 5 reviews
                review_data.append( {
                    'text': review.get( 'text', '' ),
                    'rating': review.get( 'rating', 0 ),
                    'author_name': review.get( 'author_name', 'Anonymous' ),
                    'relative_time_description': review.get( 'relative_time_description', 'recently' )
                } );
                
            # Perform sentiment analysis
            analysis = self.sentiment_analyzer.analyze_reviews( review_data );
            
            # Store results in place_data
            place_data.sentiment_avg = analysis.get( 'sentiment_avg' );
            place_data.sentiment_distribution = analysis.get( 'sentiment_distribution' );
            place_data.review_keywords = analysis.get( 'top_keywords' );
            place_data.sentiment_summary = analysis.get( 'analysis_summary' );
            
            # Create enhanced review summary
            place_data.review_summary = self._create_enhanced_review_summary( analysis, reviews );
            
        except Exception as e:
            logger.warning( f"Error analyzing reviews: {e}" );
            place_data.review_summary = self._create_basic_review_summary( reviews );

    def _create_basic_review_summary( self, reviews: List[Dict] ) -> str:
        """Create basic review summary without sentiment analysis."""
        if not reviews:
            return None;
            
        # Get average rating and count
        ratings = [ r.get( 'rating', 0 ) for r in reviews if r.get( 'rating' ) ];
        avg_rating = sum( ratings ) / len( ratings ) if ratings else 0;
        
        # Get some review snippets
        snippets = [];
        for review in reviews[ :3 ]:
            text = review.get( 'text', '' );
            if text and len( text ) > 10:
                # Get first sentence or first 100 chars
                first_sentence = text.split( '.' )[ 0 ];
                snippet = first_sentence if len( first_sentence ) < 100 else text[ :97 ] + '...';
                snippets.append( snippet );
                
        snippet_text = ' | '.join( snippets );
        return f"Average rating: {avg_rating:.1f}/5. Recent reviews: {snippet_text}";

    def _create_enhanced_review_summary( self, analysis: Dict, reviews: List[Dict] ) -> str:
        """Create enhanced review summary with sentiment analysis."""
        sentiment_dist = analysis.get( 'sentiment_distribution', {} );
        keywords = analysis.get( 'top_keywords', [] );
        
        positive_pct = sentiment_dist.get( 'positive', 0 );
        review_count = len( reviews );
        
        summary_parts = [];
        
        # Overall sentiment
        if positive_pct >= 70:
            summary_parts.append( f"Generally positive reviews ({positive_pct}% positive)" );
        elif positive_pct >= 50:
            summary_parts.append( f"Mixed reviews ({positive_pct}% positive)" );
        else:
            summary_parts.append( f"Mixed to negative reviews ({positive_pct}% positive)" );
            
        # Key topics
        if keywords:
            summary_parts.append( f"Key topics: {', '.join( keywords[ :3 ] )}" );
            
        # Review count
        summary_parts.append( f"Based on {review_count} recent reviews" );
        
        return '. '.join( summary_parts );

    def enrich_restaurant_data( self, business_name: str, address: str ) -> Optional[PlaceData]:
        """
        Complete workflow to enrich restaurant data from Google Places.
        
        Args:
            business_name: Name of the restaurant
            address: Address of the restaurant
            
        Returns:
            PlaceData object with enriched information or None if not found
        """
        logger.info( f"Enriching data for restaurant: {business_name} at {address}" );
        
        try:
            # Step 1: Search for place
            place_id = self.search_place( business_name, address );
            if not place_id:
                logger.info( f"No place found for {business_name}" );
                return None;
                
            # Step 2: Get detailed information
            place_data = self.get_place_details( place_id );
            if not place_data:
                logger.warning( f"No details available for place_id: {place_id}" );
                return None;
                
            logger.info( f"Successfully enriched data for {business_name}" );
            return place_data;
            
        except Exception as e:
            self._handle_api_error( e, f"enrich_restaurant_data({business_name})" );
            return None;

    def get_quota_usage( self ) -> Dict[str, Any]:
        """Get current API quota usage and cost estimates."""
        usage = self.quota_tracker.get_usage_summary();
        
        # Add error summary if available
        if self.error_handler:
            usage[ 'error_summary' ] = self.error_handler.get_error_summary();
            
        return usage;

    def log_usage_summary( self ):
        """Log current usage summary."""
        usage = self.get_quota_usage();
        
        logger.info( f"Google Places API Usage Summary:" );
        logger.info( f"  Total calls: {usage[ 'total_calls' ]}" );
        logger.info( f"  Text search: {usage[ 'text_search_calls' ]}" );
        logger.info( f"  Place details: {usage[ 'place_details_calls' ]}" );
        logger.info( f"  Estimated cost: ${usage[ 'estimated_cost_usd' ]:.4f}" );
        
        if 'error_summary' in usage:
            logger.info( f"  Errors by category: {usage[ 'error_summary' ]}" );

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO );
    
    try:
        # Initialize client
        client = GooglePlacesClient( rate_limit_per_second=1.0 );  # Slow for testing
        
        # Test with a known restaurant
        place_data = client.enrich_restaurant_data( 
            "Joe's Kansas City Bar-B-Que",
            "3002 W 47th Ave, Kansas City, KS"
        );
        
        if place_data:
            print( f"Found: {place_data.name}" );
            print( f"Rating: {place_data.rating}" );
            print( f"Cuisine: {place_data.cuisine_type}" );
            print( f"Price Level: {place_data.price_level}" );
            if place_data.sentiment_summary:
                print( f"Sentiment: {place_data.sentiment_summary}" );
        else:
            print( "No data found" );
            
        # Log usage
        client.log_usage_summary();
        
    except Exception as e:
        print( f"Test failed: {e}" );
