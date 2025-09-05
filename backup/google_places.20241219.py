#!/usr/bin/env python3
"""
Google Places API Service Layer
Handles all interactions with Google Places API for restaurant data enrichment
"""

import os;
import logging;
import time;
import re;
from typing import Dict, List, Optional, Tuple;
from dataclasses import dataclass;

try:
    from .sentiment_analyzer import SentimentAnalyzer;
    SENTIMENT_AVAILABLE = True;
except ImportError:
    print( "Sentiment analyzer not available. Install textblob and nltk." );
    SENTIMENT_AVAILABLE = False;

try:
    import googlemaps;
    GOOGLEMAPS_AVAILABLE = True;
except ImportError:
    print( "googlemaps is not installed. Please install it using 'pip install googlemaps'." );
    GOOGLEMAPS_AVAILABLE = False;

logger = logging.getLogger( __name__ );

@dataclass
class PlaceData:
    """Structured representation of Google Places data for a restaurant."""
    place_id: Optional[str] = None;
    name: Optional[str] = None;
    formatted_address: Optional[str] = None;
    rating: Optional[float] = None;
    review_count: Optional[int] = None;
    price_level: Optional[int] = None;
    latitude: Optional[float] = None;
    longitude: Optional[float] = None;
    cuisine_type: Optional[str] = None;
    outdoor_seating: Optional[bool] = None;
    takeout_available: Optional[bool] = None;
    delivery_available: Optional[bool] = None;
    reservations_accepted: Optional[bool] = None;
    wheelchair_accessible: Optional[bool] = None;
    good_for_children: Optional[bool] = None;
    serves_alcohol: Optional[bool] = None;
    parking_available: Optional[bool] = None;
    business_hours: Optional[Dict] = None;
    review_summary: Optional[str] = None;
    
    # Enhanced review analysis
    review_analysis: Optional[Dict] = None;
    sentiment_avg: Optional[float] = None;
    sentiment_distribution: Optional[Dict] = None;
    review_keywords: Optional[List[str]] = None;
    sentiment_summary: Optional[str] = None;


class GooglePlacesService:
    """Service class for Google Places API interactions."""
    
    def __init__(self, api_key: Optional[str] = None, region: str = "us"):
        """
        Initialize Google Places service.
        
        Args:
            api_key: Google Places API key. If None, will try to get from environment.
            region: Region bias for search results (default: 'us')
        """
        if not GOOGLEMAPS_AVAILABLE:
            raise ImportError( "googlemaps library is required. Install with: pip install googlemaps" );
            
        self.api_key = api_key or os.getenv( 'GOOGLE_PLACES_API_KEY' );
        if not self.api_key:
            raise ValueError( "Google Places API key is required. Set GOOGLE_PLACES_API_KEY environment variable." );
            
        self.region = region;
        self.client = googlemaps.Client( key=self.api_key );
        
        # Rate limiting
        self.last_request_time = 0;
        self.min_request_interval = 0.01;  # 100 requests per second max
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = None;
        if SENTIMENT_AVAILABLE:
            try:
                self.sentiment_analyzer = SentimentAnalyzer();
                logger.info( "Sentiment analyzer initialized" );
            except Exception as e:
                logger.warning( f"Could not initialize sentiment analyzer: {e}" );
        
        logger.info( f"Google Places service initialized with region: {region}" );

    def _rate_limit(self) -> None:
        """Enforce rate limiting for API requests."""
        current_time = time.time();
        time_since_last = current_time - self.last_request_time;
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last;
            time.sleep( sleep_time );
        self.last_request_time = time.time();

    def search_place(self, business_name: str, address: str, max_retries: int = 3) -> Optional[str]:
        """
        Search for a place and return its place_id.
        
        Args:
            business_name: Name of the business to search for
            address: Address of the business  
            max_retries: Maximum number of retry attempts
            
        Returns:
            Google place_id if found, None otherwise
        """
        if not business_name or not address:
            logger.warning( "Empty business name or address provided for search" );
            return None;

        # Construct search query
        query = f"{business_name} {address}".strip();
        logger.debug( f"Searching for place: {query}" );

        for attempt in range( max_retries ):
            try:
                self._rate_limit();
                
                # Use Text Search API for better results
                results = self.client.places( query=query, type='restaurant', region=self.region );
                
                if results.get( 'results' ):
                    # Return the first result's place_id
                    place_id = results['results'][0]['place_id'];
                    logger.debug( f"Found place_id: {place_id} for query: {query}" );
                    return place_id;
                else:
                    logger.info( f"No results found for query: {query}" );
                    return None;
                    
            except googlemaps.exceptions.ApiError as e:
                logger.error( f"Google Places API error (attempt {attempt + 1}): {e}" );
                if attempt < max_retries - 1:
                    time.sleep( (2 ** attempt) );  # Exponential backoff
                else:
                    raise;
            except Exception as e:
                logger.error( f"Unexpected error searching for place (attempt {attempt + 1}): {e}" );
                if attempt < max_retries - 1:
                    time.sleep( (2 ** attempt) );
                else:
                    return None;

        return None;

    def get_place_details(self, place_id: str, max_retries: int = 3) -> Optional[PlaceData]:
        """
        Get detailed information about a place.
        
        Args:
            place_id: Google place_id
            max_retries: Maximum number of retry attempts
            
        Returns:
            PlaceData object with all available information
        """
        if not place_id:
            logger.warning( "Empty place_id provided" );
            return None;

        # Define fields to retrieve
        fields = [
            'place_id', 'name', 'formatted_address', 'geometry',
            'rating', 'user_ratings_total', 'price_level', 'types',
            'opening_hours', 'reviews', 'serves_beer', 'serves_wine',
            'takeout', 'delivery', 'dine_in', 'reservable',
            'wheelchair_accessible_entrance'
        ];

        for attempt in range( max_retries ):
            try:
                self._rate_limit();
                
                result = self.client.place( place_id=place_id, fields=fields );
                
                if result.get( 'result' ):
                    place_data = self._parse_place_details( result['result'] );
                    logger.debug( f"Retrieved details for place_id: {place_id}" );
                    return place_data;
                else:
                    logger.warning( f"No result found for place_id: {place_id}" );
                    return None;
                    
            except googlemaps.exceptions.ApiError as e:
                logger.error( f"Google Places API error (attempt {attempt + 1}): {e}" );
                if attempt < max_retries - 1:
                    time.sleep( (2 ** attempt) );
                else:
                    raise;
            except Exception as e:
                logger.error( f"Unexpected error getting place details (attempt {attempt + 1}): {e}" );
                if attempt < max_retries - 1:
                    time.sleep( (2 ** attempt) );
                else:
                    return None;

        return None;

    def _parse_place_details(self, place_result: Dict) -> PlaceData:
        """
        Parse Google Places API result into structured PlaceData.
        
        Args:
            place_result: Raw result from Google Places API
            
        Returns:
            PlaceData object with parsed information
        """
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
        
        # Determine cuisine type from types array
        data.cuisine_type = self._determine_cuisine_type( place_result.get( 'types', [] ) );
        
        # Parse amenities
        data.outdoor_seating = self._extract_outdoor_seating( place_result );
        data.takeout_available = place_result.get( 'takeout' );
        data.delivery_available = place_result.get( 'delivery' );
        data.reservations_accepted = place_result.get( 'reservable' );
        data.wheelchair_accessible = place_result.get( 'wheelchair_accessible_entrance' );
        data.serves_alcohol = place_result.get( 'serves_beer' ) or place_result.get( 'serves_wine' );
        
        # Business hours
        data.business_hours = self._parse_business_hours( place_result.get( 'opening_hours' ) );
        
        # Enhanced review analysis with sentiment
        reviews_data = place_result.get( 'reviews', [] );
        data.review_summary = self._get_review_summary( reviews_data );
        
        if self.sentiment_analyzer and reviews_data:
            try:
                analysis = self.sentiment_analyzer.analyze_reviews( reviews_data );
                data.review_analysis = analysis;
                data.sentiment_avg = analysis.get( 'sentiment_avg' );
                data.sentiment_distribution = analysis.get( 'sentiment_distribution' );
                data.review_keywords = analysis.get( 'top_keywords' );
                data.sentiment_summary = analysis.get( 'analysis_summary' );
                logger.debug( f"Sentiment analysis completed: {analysis.get('reviews_count')} reviews" );
            except Exception as e:
                logger.warning( f"Error in sentiment analysis: {e}" );
        else:
            logger.debug( "Sentiment analysis skipped (no analyzer or reviews)" );
        
        # Additional amenities inference
        data.good_for_children = self._infer_child_friendly( place_result );
        data.parking_available = self._infer_parking_available( place_result );
        
        return data;

    def _determine_cuisine_type(self, types: List[str]) -> Optional[str]:
        """
        Determine primary cuisine type from Google Places types array.
        
        Args:
            types: List of type strings from Google Places
            
        Returns:
            Primary cuisine type or None
        """
        # Cuisine type mapping
        cuisine_mapping = {
            'chinese_restaurant': 'Chinese',
            'japanese_restaurant': 'Japanese',
            'korean_restaurant': 'Korean',
            'thai_restaurant': 'Thai',
            'vietnamese_restaurant': 'Vietnamese',
            'indian_restaurant': 'Indian',
            'mexican_restaurant': 'Mexican',
            'italian_restaurant': 'Italian',
            'french_restaurant': 'French',
            'greek_restaurant': 'Greek',
            'mediterranean_restaurant': 'Mediterranean',
            'middle_eastern_restaurant': 'Middle Eastern',
            'american_restaurant': 'American',
            'southern_restaurant': 'Southern',
            'seafood_restaurant': 'Seafood',
            'steak_house': 'Steakhouse',
            'barbecue_restaurant': 'BBQ',
            'pizza_restaurant': 'Pizza',
            'hamburger_restaurant': 'Burgers',
            'sandwich_shop': 'Sandwiches',
            'coffee_shop': 'Coffee',
            'bakery': 'Bakery',
            'ice_cream_shop': 'Ice Cream',
            'fast_food_restaurant': 'Fast Food'
        };
        
        for place_type in types:
            if place_type in cuisine_mapping:
                return cuisine_mapping[place_type];
        
        # If no specific cuisine found, check for general restaurant types
        if 'restaurant' in types:
            return 'American';  # Default for unspecified restaurants
        elif 'food' in types:
            return 'Food';
            
        return None;

    def _extract_outdoor_seating(self, place_result: Dict) -> Optional[bool]:
        """
        Attempt to determine if place has outdoor seating.
        This is not directly available in Google Places API, so we use heuristics.
        """
        # Check if outdoor seating is mentioned in reviews
        reviews = place_result.get( 'reviews', [] );
        outdoor_keywords = ['outdoor', 'patio', 'terrace', 'deck', 'garden', 'outside'];
        
        for review in reviews[:3]:  # Check first 3 reviews
            text = review.get( 'text', '' ).lower();
            if any( keyword in text for keyword in outdoor_keywords ):
                return True;
        
        return None;  # Unknown

    def _parse_business_hours(self, opening_hours: Optional[Dict]) -> Optional[Dict]:
        """
        Parse business hours into structured format.
        
        Args:
            opening_hours: Opening hours data from Google Places
            
        Returns:
            Structured hours dictionary or None
        """
        if not opening_hours:
            return None;
            
        try:
            weekday_text = opening_hours.get( 'weekday_text', [] );
            periods = opening_hours.get( 'periods', [] );
            
            return {
                'weekday_text': weekday_text,
                'periods': periods,
                'open_now': opening_hours.get( 'open_now' )
            };
        except Exception as e:
            logger.warning( f"Error parsing business hours: {e}" );
            return None;

    def _get_review_summary(self, reviews: List[Dict]) -> Optional[str]:
        """
        Create a summary from the top 3 reviews.
        
        Args:
            reviews: List of review objects from Google Places
            
        Returns:
            Summary string of top reviews or None
        """
        if not reviews:
            return None;
            
        try:
            # Get first 3 reviews, limit text length
            summaries = [];
            for review in reviews[:3]:
                text = review.get( 'text', '' );
                rating = review.get( 'rating', 0 );
                # Truncate long reviews
                if len( text ) > 100:
                    text = text[:97] + "...";
                summaries.append( f"({rating}★) {text}" );
            
            return " | ".join( summaries );
        except Exception as e:
            logger.warning( f"Error creating review summary: {e}" );
            return None;

    def _infer_child_friendly(self, place_result: Dict) -> Optional[bool]:
        """
        Infer if place is child-friendly from available data.
        """
        types = place_result.get( 'types', [] );
        name = place_result.get( 'name', '' ).lower();
        
        # Family-friendly indicators
        family_types = ['family_restaurant'];
        family_keywords = ['family', 'kids', 'children'];
        
        if any( t in types for t in family_types ):
            return True;
        if any( keyword in name for keyword in family_keywords ):
            return True;
            
        # Fast food chains are generally child-friendly
        if 'fast_food_restaurant' in types:
            return True;
            
        return None;  # Unknown

    def _infer_parking_available(self, place_result: Dict) -> Optional[bool]:
        """
        Infer parking availability from available data.
        """
        # This would require additional Place Details fields that may not be available
        # For now, return None (unknown)
        return None;

    def enrich_restaurant_data(self, business_name: str, address: str) -> Optional[PlaceData]:
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
            logger.error( f"Error enriching restaurant data for {business_name}: {e}" );
            return None;


def rating_to_grade(rating: Optional[float]) -> Optional[str]:
    """
    Convert numeric rating to letter grade.
    
    Args:
        rating: Numeric rating (1-5 scale)
        
    Returns:
        Letter grade (A+ to F) or None
    """
    if rating is None:
        return None;
        
    if rating >= 4.6:
        return "A+";
    elif rating >= 4.4:
        return "A";
    elif rating >= 4.2:
        return "A-";
    elif rating >= 4.0:
        return "B+";
    elif rating >= 3.8:
        return "B";
    elif rating >= 3.6:
        return "B-";
    elif rating >= 3.4:
        return "C+";
    elif rating >= 3.2:
        return "C";
    elif rating >= 3.0:
        return "C-";
    elif rating >= 2.5:
        return "D";
    else:
        return "F";


# Example usage and testing
if __name__ == "__main__":
    # Basic test
    logging.basicConfig( level=logging.DEBUG );
    
    try:
        service = GooglePlacesService();
        
        # Test search
        test_data = service.enrich_restaurant_data( 
            "Joe's Kansas City Bar-B-Que",
            "3002 W 47th Ave, Kansas City, KS"
        );
        
        if test_data:
            print( f"Found: {test_data.name}" );
            print( f"Rating: {test_data.rating} ({rating_to_grade(test_data.rating)})" );
            print( f"Cuisine: {test_data.cuisine_type}" );
            print( f"Price Level: {test_data.price_level}" );
        else:
            print( "No data found" );
            
    except Exception as e:
        print( f"Test failed: {e}" );
