#!/usr/bin/env python3
"""
AI Restaurant Rating Predictor
Uses nearby restaurants and cuisine matching to predict ratings for new restaurants
"""

import math;
import logging;
from typing import Dict, List, Optional, Tuple, Any;
from dataclasses import dataclass;

logger = logging.getLogger( __name__ );

@dataclass
class PredictionFeatures:
    """Features used for prediction"""
    latitude: float;
    longitude: float;
    cuisine_type: Optional[str];
    price_level: Optional[int];
    outdoor_seating: Optional[bool];
    takeout_available: Optional[bool];
    delivery_available: Optional[bool];
    reservations_accepted: Optional[bool];
    wheelchair_accessible: Optional[bool];
    good_for_children: Optional[bool];
    serves_alcohol: Optional[bool];
    parking_available: Optional[bool];

@dataclass
class SimilarRestaurant:
    """Similar restaurant used for prediction"""
    name: str;
    distance_miles: float;
    cuisine_match: bool;
    rating: float;
    review_count: int;
    similarity_score: float;
    weight: float;

class RestaurantAIPredictor:
    """AI-powered restaurant rating prediction based on nearby restaurants and features"""
    
    def __init__( self, mongodb_collection=None ):
        self.collection = mongodb_collection;
        self.logger = logging.getLogger( self.__class__.__name__ );
        
        # Prediction parameters
        self.max_proximity_miles = 5.0;  # Max distance for proximity-based predictions
        self.max_cuisine_miles = 7.0;    # Max distance for cuisine-type matching
        self.min_similar_restaurants = 3;  # Minimum restaurants needed for prediction
        
        # Weight factors for prediction
        self.weights = {
            'proximity': 0.4,      # Weight for geographic proximity
            'cuisine_match': 0.3,  # Weight for same cuisine type
            'amenity_match': 0.2,  # Weight for similar amenities
            'review_volume': 0.1   # Weight for number of reviews
        };
    
    def calculate_distance( self, lat1: float, lon1: float, lat2: float, lon2: float ) -> float:
        """
        Calculate approximate distance between two lat/lon points in miles.
        Uses simple Euclidean distance approximation, not accounting for Earth's curvature.
        Good enough for distances under 100 miles.
        """
        # Approximate conversion: 1 degree ≈ 69 miles at mid-latitudes
        lat_miles_per_degree = 69.0;
        lon_miles_per_degree = 69.0 * math.cos( math.radians( ( lat1 + lat2 ) / 2 ) );
        
        lat_diff = ( lat2 - lat1 ) * lat_miles_per_degree;
        lon_diff = ( lon2 - lon1 ) * lon_miles_per_degree;
        
        distance = math.sqrt( lat_diff * lat_diff + lon_diff * lon_diff );
        return distance;
    
    def calculate_amenity_similarity( self, features1: PredictionFeatures, features2: Dict ) -> float:
        """Calculate similarity between amenities (0.0 to 1.0)"""
        amenity_fields = [
            'outdoor_seating', 'takeout_available', 'delivery_available',
            'reservations_accepted', 'wheelchair_accessible', 'good_for_children',
            'serves_alcohol', 'parking_available'
        ];
        
        matches = 0;
        total_comparisons = 0;
        
        for field in amenity_fields:
            value1 = getattr( features1, field, None );
            value2 = features2.get( field );
            
            # Only compare if both values are available
            if value1 is not None and value2 is not None:
                total_comparisons += 1;
                if value1 == value2:
                    matches += 1;
        
        if total_comparisons == 0:
            return 0.5;  # Neutral similarity if no comparisons possible
            
        return matches / total_comparisons;
    
    def find_similar_restaurants( self, features: PredictionFeatures ) -> List[SimilarRestaurant]:
        """Find similar restaurants based on proximity, cuisine, and amenities"""
        if not self.collection:
            self.logger.warning( "No MongoDB collection provided, cannot find similar restaurants" );
            return [];
        
        similar_restaurants = [];
        
        try:
            # Query for restaurants with ratings within a reasonable radius
            # We'll use a bounding box for initial filtering, then calculate exact distances
            lat_delta = self.max_cuisine_miles / 69.0;  # Rough degree conversion
            lon_delta = self.max_cuisine_miles / ( 69.0 * math.cos( math.radians( features.latitude ) ) );
            
            query = {
                'google_rating': { '$exists': True, '$ne': None },
                'latitude': { 
                    '$gte': features.latitude - lat_delta,
                    '$lte': features.latitude + lat_delta
                },
                'longitude': {
                    '$gte': features.longitude - lon_delta,
                    '$lte': features.longitude + lon_delta
                }
            };
            
            restaurants = self.collection.find( query );
            
            for restaurant in restaurants:
                if not restaurant.get( 'latitude' ) or not restaurant.get( 'longitude' ):
                    continue;
                    
                # Calculate actual distance
                distance = self.calculate_distance(
                    features.latitude, features.longitude,
                    restaurant[ 'latitude' ], restaurant[ 'longitude' ]
                );
                
                # Skip if too far for any type of prediction
                if distance > self.max_cuisine_miles:
                    continue;
                
                # Check cuisine match
                restaurant_cuisine = restaurant.get( 'cuisine_type' );
                cuisine_match = ( 
                    features.cuisine_type and 
                    restaurant_cuisine and 
                    features.cuisine_type.lower() == restaurant_cuisine.lower()
                );
                
                # Apply distance limits based on whether it's a cuisine match
                max_distance = self.max_cuisine_miles if cuisine_match else self.max_proximity_miles;
                if distance > max_distance:
                    continue;
                
                # Calculate amenity similarity
                amenity_similarity = self.calculate_amenity_similarity( features, restaurant );
                
                # Calculate overall similarity score
                similarity_score = 0.0;
                
                # Proximity component (closer = better)
                proximity_score = max( 0, 1.0 - ( distance / max_distance ) );
                similarity_score += self.weights[ 'proximity' ] * proximity_score;
                
                # Cuisine match component
                cuisine_score = 1.0 if cuisine_match else 0.3;  # Small bonus even for non-matches
                similarity_score += self.weights[ 'cuisine_match' ] * cuisine_score;
                
                # Amenity similarity component
                similarity_score += self.weights[ 'amenity_match' ] * amenity_similarity;
                
                # Review volume component (more reviews = more reliable)
                review_count = restaurant.get( 'google_user_ratings_total', 0 );
                review_score = min( 1.0, review_count / 100.0 );  # Normalize to 0-1
                similarity_score += self.weights[ 'review_volume' ] * review_score;
                
                # Calculate prediction weight (higher similarity = higher weight)
                weight = similarity_score * ( 1.0 / max( 0.1, distance ) );  # Distance penalty
                
                similar_restaurant = SimilarRestaurant(
                    name=restaurant.get( 'business_name', 'Unknown' ),
                    distance_miles=distance,
                    cuisine_match=cuisine_match,
                    rating=restaurant.get( 'google_rating', 3.5 ),
                    review_count=review_count,
                    similarity_score=similarity_score,
                    weight=weight
                );
                
                similar_restaurants.append( similar_restaurant );
            
            # Sort by similarity score (highest first)
            similar_restaurants.sort( key=lambda x: x.similarity_score, reverse=True );
            
            self.logger.debug( f"Found {len( similar_restaurants )} similar restaurants for prediction" );
            
        except Exception as e:
            self.logger.error( f"Error finding similar restaurants: {e}" );
        
        return similar_restaurants;
    
    def predict_rating( self, features: PredictionFeatures ) -> Tuple[float, str, List[SimilarRestaurant]]:
        """
        Predict restaurant rating based on similar restaurants
        
        Returns:
            Tuple of (predicted_rating, confidence_level, similar_restaurants_used)
        """
        similar_restaurants = self.find_similar_restaurants( features );
        
        if len( similar_restaurants ) < self.min_similar_restaurants:
            # Not enough data for prediction, return default
            default_rating = 3.7;  # Slightly above average
            confidence = "Low - insufficient nearby data";
            self.logger.debug( f"Insufficient similar restaurants ({len( similar_restaurants )}) for prediction, using default rating" );
            return default_rating, confidence, similar_restaurants;
        
        # Calculate weighted average rating
        total_weighted_rating = 0.0;
        total_weight = 0.0;
        cuisine_matches = 0;
        proximity_matches = 0;
        
        for restaurant in similar_restaurants:
            total_weighted_rating += restaurant.rating * restaurant.weight;
            total_weight += restaurant.weight;
            
            if restaurant.cuisine_match:
                cuisine_matches += 1;
            if restaurant.distance_miles <= self.max_proximity_miles:
                proximity_matches += 1;
        
        if total_weight == 0:
            predicted_rating = 3.7;
        else:
            predicted_rating = total_weighted_rating / total_weight;
        
        # Determine confidence level
        if cuisine_matches >= 3 and proximity_matches >= 2:
            confidence = "High - strong cuisine and proximity matches";
        elif cuisine_matches >= 2 or proximity_matches >= 3:
            confidence = "Medium - good local or cuisine data";
        elif len( similar_restaurants ) >= 5:
            confidence = "Medium - sufficient nearby data";
        else:
            confidence = "Low - limited comparison data";
        
        # Clamp rating to reasonable bounds
        predicted_rating = max( 1.0, min( 5.0, predicted_rating ) );
        
        self.logger.info( f"Predicted rating: {predicted_rating:.2f} ({confidence}) based on {len( similar_restaurants )} similar restaurants" );
        
        return predicted_rating, confidence, similar_restaurants;
    
    def predict_grade( self, rating: float ) -> str:
        """Convert predicted rating to letter grade"""
        if rating >= 4.5:
            return 'A+';
        elif rating >= 4.2:
            return 'A';
        elif rating >= 3.8:
            return 'A-';
        elif rating >= 3.5:
            return 'B+';
        elif rating >= 3.2:
            return 'B';
        elif rating >= 2.8:
            return 'B-';
        elif rating >= 2.5:
            return 'C+';
        elif rating >= 2.0:
            return 'C';
        elif rating >= 1.5:
            return 'C-';
        else:
            return 'D';
    
    def retrain_prediction( self, features: PredictionFeatures, actual_rating: float ) -> Dict[str, Any]:
        """
        Retrain/improve predictions when actual rating becomes available
        This is a framework for future model improvement
        """
        predicted_rating, confidence, similar_restaurants = self.predict_rating( features );
        
        error = abs( actual_rating - predicted_rating );
        
        # Calculate prediction accuracy metrics
        accuracy_info = {
            'predicted_rating': predicted_rating,
            'actual_rating': actual_rating,
            'error': error,
            'confidence_level': confidence,
            'similar_restaurants_count': len( similar_restaurants ),
            'accuracy_category': 'excellent' if error <= 0.3 else 'good' if error <= 0.6 else 'poor'
        };
        
        self.logger.info( f"Prediction accuracy: {accuracy_info[ 'accuracy_category' ]} (error: {error:.2f})" );
        
        # TODO: In future versions, we could:
        # 1. Adjust weight factors based on prediction accuracy
        # 2. Store prediction results in a separate collection for analysis
        # 3. Implement machine learning model retraining
        
        return accuracy_info;
    
    def get_prediction_explanation( self, features: PredictionFeatures, similar_restaurants: List[SimilarRestaurant] ) -> str:
        """Generate human-readable explanation of prediction"""
        if not similar_restaurants:
            return "Prediction based on default ratings due to insufficient nearby restaurant data.";
        
        cuisine_matches = [ r for r in similar_restaurants if r.cuisine_match ];
        nearby_restaurants = [ r for r in similar_restaurants if r.distance_miles <= 2.0 ];
        
        explanation_parts = [];
        
        if cuisine_matches:
            avg_cuisine_rating = sum( r.rating for r in cuisine_matches ) / len( cuisine_matches );
            explanation_parts.append( f"{len( cuisine_matches )} {features.cuisine_type} restaurants averaging {avg_cuisine_rating:.1f} stars" );
        
        if nearby_restaurants:
            avg_nearby_rating = sum( r.rating for r in nearby_restaurants ) / len( nearby_restaurants );
            explanation_parts.append( f"{len( nearby_restaurants )} nearby restaurants averaging {avg_nearby_rating:.1f} stars" );
        
        if len( similar_restaurants ) > len( cuisine_matches ) + len( nearby_restaurants ):
            other_count = len( similar_restaurants ) - len( cuisine_matches ) - len( nearby_restaurants );
            explanation_parts.append( f"{other_count} other area restaurants" );
        
        explanation = f"Based on " + ", ".join( explanation_parts );
        
        # Add distance context
        closest_distance = min( r.distance_miles for r in similar_restaurants );
        farthest_distance = max( r.distance_miles for r in similar_restaurants );
        explanation += f" within {closest_distance:.1f}-{farthest_distance:.1f} miles.";
        
        return explanation;
