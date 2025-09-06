#!/usr/bin/env python3
"""
AI Model Retraining Service
Framework for improving predictions when actual ratings become available
"""

import logging;
from typing import Dict, List, Optional, Any;
from datetime import datetime;

logger = logging.getLogger( __name__ );

class ModelTrainer:
    """Service for retraining AI prediction models based on actual vs predicted data"""
    
    def __init__( self, mongodb_collection=None ):
        self.collection = mongodb_collection;
        self.logger = logging.getLogger( self.__class__.__name__ );
        
        # Training statistics
        self.training_stats = {
            'total_comparisons': 0,
            'excellent_predictions': 0,
            'good_predictions': 0,
            'poor_predictions': 0,
            'average_error': 0.0,
            'last_training_date': None
        };
    
    def record_prediction_accuracy( self, restaurant_data: Dict[str, Any] ) -> Dict[str, Any]:
        """
        Record prediction accuracy when actual rating becomes available
        
        Args:
            restaurant_data: Restaurant document with both predicted and actual ratings
            
        Returns:
            Dictionary with accuracy analysis
        """
        predicted_rating = restaurant_data.get( 'ai_predicted_rating' );
        actual_rating = restaurant_data.get( 'google_rating' );
        
        if not predicted_rating or not actual_rating:
            return { 'status': 'insufficient_data' };
            
        # Calculate prediction error
        error = abs( actual_rating - predicted_rating );
        
        # Categorize accuracy
        if error <= 0.3:
            accuracy_category = 'excellent';
            self.training_stats[ 'excellent_predictions' ] += 1;
        elif error <= 0.6:
            accuracy_category = 'good';
            self.training_stats[ 'good_predictions' ] += 1;
        else:
            accuracy_category = 'poor';
            self.training_stats[ 'poor_predictions' ] += 1;
        
        # Update overall statistics
        self.training_stats[ 'total_comparisons' ] += 1;
        
        # Update running average error
        total_comparisons = self.training_stats[ 'total_comparisons' ];
        self.training_stats[ 'average_error' ] = (
            ( self.training_stats[ 'average_error' ] * ( total_comparisons - 1 ) + error ) / total_comparisons
        );
        
        accuracy_info = {
            'status': 'recorded',
            'predicted_rating': predicted_rating,
            'actual_rating': actual_rating,
            'error': error,
            'accuracy_category': accuracy_category,
            'restaurant_name': restaurant_data.get( 'business_name', 'Unknown' ),
            'cuisine_type': restaurant_data.get( 'cuisine_type' ),
            'prediction_confidence': restaurant_data.get( 'ai_prediction_confidence' )
        };
        
        self.logger.info( f"Recorded prediction accuracy: {accuracy_category} (error: {error:.2f}) for {restaurant_data.get( 'business_name', 'Unknown' )}" );
        
        return accuracy_info;
    
    def analyze_prediction_patterns( self ) -> Dict[str, Any]:
        """
        Analyze prediction patterns to identify improvement opportunities
        
        Returns:
            Analysis report with recommendations
        """
        if not self.collection:
            return { 'status': 'no_database_connection' };
            
        try:
            # Find restaurants with both predicted and actual ratings
            pipeline = [
                {
                    '$match': {
                        'ai_predicted_rating': { '$exists': True },
                        'google_rating': { '$exists': True },
                        'ai_predicted_rating': { '$ne': None },
                        'google_rating': { '$ne': None }
                    }
                },
                {
                    '$addFields': {
                        'prediction_error': {
                            '$abs': {
                                '$subtract': [ '$google_rating', '$ai_predicted_rating' ]
                            }
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_predictions': { '$sum': 1 },
                        'average_error': { '$avg': '$prediction_error' },
                        'max_error': { '$max': '$prediction_error' },
                        'min_error': { '$min': '$prediction_error' },
                        'excellent_predictions': {
                            '$sum': {
                                '$cond': [ { '$lte': [ '$prediction_error', 0.3 ] }, 1, 0 ]
                            }
                        },
                        'good_predictions': {
                            '$sum': {
                                '$cond': [
                                    { '$and': [
                                        { '$gt': [ '$prediction_error', 0.3 ] },
                                        { '$lte': [ '$prediction_error', 0.6 ] }
                                    ] },
                                    1, 0
                                ]
                            }
                        },
                        'poor_predictions': {
                            '$sum': {
                                '$cond': [ { '$gt': [ '$prediction_error', 0.6 ] }, 1, 0 ]
                            }
                        }
                    }
                }
            ];
            
            results = list( self.collection.aggregate( pipeline ) );
            
            if not results:
                return {
                    'status': 'no_training_data',
                    'total_predictions': 0,
                    'message': 'No restaurants with both predicted and actual ratings found'
                };
                
            analysis = results[ 0 ];
            analysis[ 'status' ] = 'completed';
            analysis[ 'analysis_date' ] = datetime.now().isoformat();
            
            # Calculate accuracy percentages
            total = analysis[ 'total_predictions' ];
            if total > 0:
                analysis[ 'excellent_percentage' ] = ( analysis[ 'excellent_predictions' ] / total ) * 100;
                analysis[ 'good_percentage' ] = ( analysis[ 'good_predictions' ] / total ) * 100;
                analysis[ 'poor_percentage' ] = ( analysis[ 'poor_predictions' ] / total ) * 100;
                
                # Overall accuracy score
                analysis[ 'overall_accuracy_score' ] = (
                    ( analysis[ 'excellent_predictions' ] * 1.0 +
                      analysis[ 'good_predictions' ] * 0.7 +
                      analysis[ 'poor_predictions' ] * 0.3 ) / total
                );
                
            # Recommendations
            recommendations = [];
            
            if analysis[ 'average_error' ] > 0.5:
                recommendations.append( "High average error suggests need for algorithm refinement" );
                
            if analysis.get( 'poor_percentage', 0 ) > 20:
                recommendations.append( "High percentage of poor predictions - consider adjusting weight factors" );
                
            if total < 10:
                recommendations.append( "Limited training data - predictions will improve with more actual ratings" );
            elif total >= 50:
                recommendations.append( "Sufficient training data available for comprehensive model improvements" );
                
            analysis[ 'recommendations' ] = recommendations;
            
            self.logger.info( f"Prediction analysis complete: {total} comparisons, {analysis.get( 'average_error', 0 ):.3f} avg error" );
            
            return analysis;
            
        except Exception as e:
            self.logger.error( f"Error analyzing prediction patterns: {e}" );
            return { 'status': 'error', 'message': str( e ) };
    
    def suggest_model_improvements( self, analysis: Dict[str, Any] ) -> List[str]:
        """
        Suggest specific model improvements based on analysis
        
        Args:
            analysis: Results from analyze_prediction_patterns()
            
        Returns:
            List of specific improvement suggestions
        """
        suggestions = [];
        
        if analysis.get( 'status' ) != 'completed':
            return [ "Run prediction analysis first to get improvement suggestions" ];
            
        avg_error = analysis.get( 'average_error', 0 );
        total_predictions = analysis.get( 'total_predictions', 0 );
        poor_percentage = analysis.get( 'poor_percentage', 0 );
        
        # Error-based suggestions
        if avg_error > 0.7:
            suggestions.append( "Consider increasing proximity weight factor from 0.4 to 0.5" );
            suggestions.append( "Reduce cuisine match weight from 0.3 to 0.2 for broader data inclusion" );
        elif avg_error > 0.5:
            suggestions.append( "Fine-tune amenity matching algorithm - current weight may be too high" );
            suggestions.append( "Consider expanding search radius for cuisine matches from 7 to 8 miles" );
        elif avg_error < 0.2:
            suggestions.append( "Excellent accuracy! Consider tightening proximity radius for more precise predictions" );
            
        # Volume-based suggestions
        if total_predictions < 10:
            suggestions.append( "Collect more actual ratings to improve model reliability" );
        elif total_predictions >= 50:
            suggestions.append( "Sufficient data for implementing machine learning enhancements" );
            suggestions.append( "Consider implementing weighted learning based on prediction confidence levels" );
            
        # Quality-based suggestions
        if poor_percentage > 30:
            suggestions.append( "High error rate - consider implementing restaurant category-specific models" );
            suggestions.append( "Add geographic clustering to improve regional accuracy" );
        elif poor_percentage < 10:
            suggestions.append( "Low error rate indicates well-tuned model - focus on edge case improvements" );
            
        # Specific algorithmic improvements
        suggestions.extend( [
            "Implement time-based weight decay for older restaurant data",
            "Add review volume confidence factor to prediction weighting",
            "Consider price level correlation analysis for cuisine-specific improvements"
        ] );
        
        return suggestions;
    
    def get_training_summary( self ) -> Dict[str, Any]:
        """Get current training statistics summary"""
        total = self.training_stats[ 'total_comparisons' ];
        
        summary = dict( self.training_stats );
        
        if total > 0:
            summary[ 'excellent_percentage' ] = ( self.training_stats[ 'excellent_predictions' ] / total ) * 100;
            summary[ 'good_percentage' ] = ( self.training_stats[ 'good_predictions' ] / total ) * 100;
            summary[ 'poor_percentage' ] = ( self.training_stats[ 'poor_predictions' ] / total ) * 100;
            
        summary[ 'last_updated' ] = datetime.now().isoformat();
        
        return summary;
