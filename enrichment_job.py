#!/usr/bin/env python3
"""
Google Places Data Enrichment Job
Standalone script to fetch and store Google Places data for restaurants missing enrichment
"""

import os;
import sys;
import logging;
import argparse;
import time;
from datetime import datetime;
from typing import Dict, List, Optional, Any;

# Add current directory to Python path for imports
sys.path.insert( 0, os.path.dirname( os.path.abspath( __file__ ) ) );

try:
    from pymongo import MongoClient;
    from pymongo.errors import ConnectionFailure;
    MONGODB_AVAILABLE = True;
except ImportError:
    print( "pymongo is not installed. Please install it using 'pip install pymongo'." );
    MONGODB_AVAILABLE = False;

try:
    from services.google_places_client import GooglePlacesClient, PlaceData;
    from utils.retry_utils import ErrorHandler, error_context;
    SERVICES_AVAILABLE = True;
except ImportError as e:
    print( f"Could not import required services: {e}" );
    print( "Make sure Google Places client and utilities are available" );
    SERVICES_AVAILABLE = False;

def setup_logging( log_file: str = None ) -> logging.Logger:
    """Configure logging for both console and file output."""
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s';
    handlers = [ logging.StreamHandler() ];
    
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname( log_file );
        if log_dir:
            os.makedirs( log_dir, exist_ok=True );
        handlers.append( logging.FileHandler( log_file ) );
        
    logging.basicConfig( 
        level=logging.INFO, 
        format=log_format, 
        handlers=handlers,
        force=True  # Override any existing configuration
    );
    
    return logging.getLogger( __name__ );

class EnrichmentJobRunner:
    """Main class for running the Google Places enrichment job."""
    
    def __init__( self, 
                 mongodb_uri: str,
                 database_name: str = "kansas_city",
                 collection_name: str = "food_businesses",
                 dry_run: bool = False,
                 batch_size: int = 10,
                 rate_limit_rps: float = 8.0 ):
        
        self.mongodb_uri = mongodb_uri;
        self.database_name = database_name;
        self.collection_name = collection_name;
        self.dry_run = dry_run;
        self.batch_size = batch_size;
        self.rate_limit_rps = rate_limit_rps;
        
        # Initialize components
        self.client = None;
        self.db = None;
        self.collection = None;
        self.google_client = None;
        self.error_handler = ErrorHandler( "EnrichmentJob" );
        
        # Job statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_restaurants': 0,
            'needs_enrichment': 0,
            'processed': 0,
            'enriched_successfully': 0,
            'enrichment_failed': 0,
            'skipped': 0,
            'api_calls_made': 0,
            'estimated_cost': 0.0
        };
        
        self.logger = logging.getLogger( self.__class__.__name__ );

    def connect_database( self ) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = MongoClient( self.mongodb_uri, serverSelectionTimeoutMS=10000 );
            self.client.admin.command( 'ping' );
            self.db = self.client[ self.database_name ];
            self.collection = self.db[ self.collection_name ];
            self.logger.info( f"Connected to MongoDB: {self.database_name}.{self.collection_name}" );
            return True;
            
        except Exception as e:
            self.logger.error( f"Failed to connect to MongoDB: {e}" );
            return False;

    def initialize_google_client( self ) -> bool:
        """Initialize Google Places client."""
        try:
            self.google_client = GooglePlacesClient( 
                rate_limit_per_second=self.rate_limit_rps,
                enable_sentiment_analysis=True
            );
            self.logger.info( f"Google Places client initialized with {self.rate_limit_rps} req/s rate limit" );
            return True;
            
        except Exception as e:
            self.logger.error( f"Failed to initialize Google Places client: {e}" );
            return False;

    def get_restaurants_needing_enrichment( self ) -> List[Dict[str, Any]]:
        """Get restaurants that need Google Places enrichment."""
        try:
            # Query for restaurants without google_place_id
            query = {
                '$or': [
                    { 'google_place_id': { '$exists': False } },
                    { 'google_place_id': None },
                    { 'google_place_id': '' }
                ]
            };
            
            # Count totals
            self.stats[ 'total_restaurants' ] = self.collection.count_documents( {} );
            self.stats[ 'needs_enrichment' ] = self.collection.count_documents( query );
            
            # Get batch of restaurants
            restaurants = list( self.collection.find( query ).limit( self.batch_size ) );
            
            self.logger.info( f"Database status:" );
            self.logger.info( f"  Total restaurants: {self.stats[ 'total_restaurants' ]:,}" );
            self.logger.info( f"  Need enrichment: {self.stats[ 'needs_enrichment' ]:,}" );
            self.logger.info( f"  Current batch: {len( restaurants )} restaurants" );
            
            return restaurants;
            
        except Exception as e:
            self.logger.error( f"Error querying restaurants: {e}" );
            return [];

    def place_data_to_dict( self, place_data: PlaceData ) -> Dict[str, Any]:
        """Convert PlaceData object to dictionary for MongoDB storage."""
        data = {};
        
        # Basic Google Places data
        if place_data.place_id: data[ 'google_place_id' ] = place_data.place_id;
        if place_data.rating: data[ 'google_rating' ] = place_data.rating;
        if place_data.review_count: data[ 'google_review_count' ] = place_data.review_count;
        if place_data.price_level is not None: data[ 'price_level' ] = place_data.price_level;
        if place_data.latitude: data[ 'latitude' ] = place_data.latitude;
        if place_data.longitude: data[ 'longitude' ] = place_data.longitude;
        if place_data.cuisine_type: data[ 'cuisine_type' ] = place_data.cuisine_type;
        
        # Amenities (only include non-null values)
        amenity_fields = [
            'outdoor_seating', 'takeout_available', 'delivery_available',
            'reservations_accepted', 'wheelchair_accessible', 'good_for_children',
            'serves_alcohol', 'parking_available'
        ];
        
        for field in amenity_fields:
            value = getattr( place_data, field, None );
            if value is not None:
                data[ field ] = value;
                
        # Business hours and summary
        if place_data.business_hours: data[ 'business_hours' ] = place_data.business_hours;
        if place_data.review_summary: data[ 'review_summary' ] = place_data.review_summary;
        
        # Sentiment analysis data
        if place_data.sentiment_avg is not None: data[ 'sentiment_avg' ] = place_data.sentiment_avg;
        if place_data.sentiment_distribution: data[ 'sentiment_distribution' ] = place_data.sentiment_distribution;
        if place_data.review_keywords: data[ 'review_keywords' ] = place_data.review_keywords;
        if place_data.sentiment_summary: data[ 'sentiment_summary' ] = place_data.sentiment_summary;
        
        # Metadata
        data[ 'places_last_updated' ] = datetime.now().isoformat();
        if place_data.api_fields_retrieved: data[ 'api_fields_retrieved' ] = place_data.api_fields_retrieved;
        
        return data;

    def enrich_restaurant( self, restaurant: Dict[str, Any] ) -> bool:
        """Enrich a single restaurant with Google Places data."""
        business_name = restaurant.get( 'business_name', '' );
        dba_name = restaurant.get( 'dba_name', '' );
        address = restaurant.get( 'address', '' );
        
        # Use DBA name if available, otherwise business name
        search_name = dba_name.strip() if dba_name.strip() else business_name.strip();
        
        if not search_name or not address:
            self.logger.warning( f"Skipping restaurant with insufficient data: {business_name}" );
            self.stats[ 'skipped' ] += 1;
            return False;
            
        self.logger.info( f"Enriching: {search_name} at {address}" );
        
        with error_context( self.error_handler, f"enrich({search_name})", reraise=False ) as ctx:
            # Get Google Places data
            place_data = self.google_client.enrich_restaurant_data( search_name, address );
            
            if not place_data:
                self.logger.info( f"No Google Places data found for: {search_name}" );
                self.stats[ 'enrichment_failed' ] += 1;
                return False;
                
            # Convert to database format
            enrichment_data = self.place_data_to_dict( place_data );
            
            if self.dry_run:
                self.logger.info( f"[DRY-RUN] Would update {search_name} with fields: {list( enrichment_data.keys() )}" );
                self.stats[ 'enriched_successfully' ] += 1;
                return True;
                
            # Update restaurant document
            result = self.collection.update_one(
                { '_id': restaurant[ '_id' ] },
                { '$set': enrichment_data }
            );
            
            if result.modified_count > 0:
                self.logger.info( f"✅ Successfully enriched: {search_name}" );
                self.stats[ 'enriched_successfully' ] += 1;
                return True;
            else:
                self.logger.warning( f"Database update failed for: {search_name}" );
                self.stats[ 'enrichment_failed' ] += 1;
                return False;
                
        # Error handling via context manager
        if ctx.category:
            self.logger.error( f"Failed to enrich {search_name}: {ctx.category.value} error" );
            self.stats[ 'enrichment_failed' ] += 1;
            return False;

    def run_enrichment_batch( self ) -> bool:
        """Run enrichment for a batch of restaurants."""
        self.logger.info( f"Starting Google Places enrichment job" );
        self.logger.info( f"Configuration: batch_size={self.batch_size}, rate_limit={self.rate_limit_rps} req/s, dry_run={self.dry_run}" );
        
        self.stats[ 'start_time' ] = datetime.now();
        
        # Get restaurants needing enrichment
        restaurants = self.get_restaurants_needing_enrichment();
        
        if not restaurants:
            self.logger.info( "No restaurants need enrichment in current batch" );
            return True;
            
        # Process each restaurant
        self.logger.info( f"Processing {len( restaurants )} restaurants..." );
        
        for i, restaurant in enumerate( restaurants ):
            self.stats[ 'processed' ] += 1;
            
            self.logger.info( f"Progress: {i + 1}/{len( restaurants )} ({((i + 1) / len( restaurants )) * 100:.1f}%)" );
            
            try:
                self.enrich_restaurant( restaurant );
                
            except KeyboardInterrupt:
                self.logger.info( "Job interrupted by user" );
                break;
            except Exception as e:
                self.logger.error( f"Unexpected error processing restaurant {restaurant.get( 'business_name', 'Unknown' )}: {e}" );
                self.stats[ 'enrichment_failed' ] += 1;
                
        self.stats[ 'end_time' ] = datetime.now();
        
        # Get API usage statistics
        if self.google_client:
            api_usage = self.google_client.get_quota_usage();
            self.stats[ 'api_calls_made' ] = api_usage.get( 'total_calls', 0 );
            self.stats[ 'estimated_cost' ] = api_usage.get( 'estimated_cost_usd', 0.0 );
            
        return True;

    def print_job_summary( self ):
        """Print comprehensive job execution summary."""
        duration = None;
        if self.stats[ 'start_time' ] and self.stats[ 'end_time' ]:
            duration = self.stats[ 'end_time' ] - self.stats[ 'start_time' ];
            
        print( "\n" + "="*80 );
        print( "🍽️  Google Places Enrichment Job - Summary Report" );
        print( "="*80 );
        
        # Basic statistics
        print( f"\n📊 Job Statistics:" );
        print( f"   Execution mode: {'DRY-RUN' if self.dry_run else 'LIVE'}" );
        print( f"   Batch size: {self.batch_size}" );
        print( f"   Rate limit: {self.rate_limit_rps} req/s" );
        if duration:
            print( f"   Duration: {duration}" );
            
        # Processing results
        print( f"\n🏪 Restaurant Processing:" );
        print( f"   Total restaurants in database: {self.stats[ 'total_restaurants' ]:,}" );
        print( f"   Restaurants needing enrichment: {self.stats[ 'needs_enrichment' ]:,}" );
        print( f"   Restaurants processed this batch: {self.stats[ 'processed' ]:,}" );
        print( f"   Successfully enriched: {self.stats[ 'enriched_successfully' ]:,}" );
        print( f"   Enrichment failed: {self.stats[ 'enrichment_failed' ]:,}" );
        print( f"   Skipped (insufficient data): {self.stats[ 'skipped' ]:,}" );
        
        # Success rate
        if self.stats[ 'processed' ] > 0:
            success_rate = ( self.stats[ 'enriched_successfully' ] / self.stats[ 'processed' ] ) * 100;
            print( f"   Success rate: {success_rate:.1f}%" );
            
        # API usage and costs
        print( f"\n💰 API Usage & Costs:" );
        print( f"   Total API calls made: {self.stats[ 'api_calls_made' ]:,}" );
        print( f"   Estimated cost: ${self.stats[ 'estimated_cost' ]:.4f}" );
        
        # Remaining work
        remaining = self.stats[ 'needs_enrichment' ] - self.stats[ 'processed' ];
        if remaining > 0:
            print( f"\n📈 Remaining Work:" );
            print( f"   Restaurants still needing enrichment: {remaining:,}" );
            if self.stats[ 'api_calls_made' ] > 0:
                # Estimate based on current batch
                avg_calls_per_restaurant = self.stats[ 'api_calls_made' ] / max( self.stats[ 'processed' ], 1 );
                estimated_calls = remaining * avg_calls_per_restaurant;
                estimated_cost = ( estimated_calls / 1000 ) * 32;  # Rough estimate
                print( f"   Estimated API calls needed: {estimated_calls:,.0f}" );
                print( f"   Estimated additional cost: ${estimated_cost:.2f}" );
                
        # Error summary
        error_summary = self.error_handler.get_error_summary();
        if error_summary:
            print( f"\n⚠️  Error Summary:" );
            for category, count in error_summary.items():
                print( f"   {category}: {count} errors" );
                
        # Next steps
        print( f"\n🚀 Next Steps:" );
        if remaining > 0:
            print( f"   • Run job again to process remaining {remaining:,} restaurants" );
            print( f"   • Consider adjusting batch size based on API quota" );
            print( f"   • Monitor API costs and adjust rate limiting if needed" );
        else:
            print( f"   • All restaurants have been processed!" );
            print( f"   • Set up scheduled runs to enrich new restaurants automatically" );
            
        # Google client usage details
        if self.google_client:
            self.google_client.log_usage_summary();
            
        print( "="*80 );

    def cleanup( self ):
        """Clean up database connections and resources."""
        if self.client:
            self.client.close();
            self.logger.info( "Database connection closed" );

def main():
    """Main function to run the enrichment job."""
    parser = argparse.ArgumentParser( 
        description='Google Places Data Enrichment Job for KC New Restaurants',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enrichment_job.py --dry-run                    # Test run without making changes
  python enrichment_job.py --batch-size 5 --rate 4     # Process 5 restaurants at 4 req/s
  python enrichment_job.py --log-file logs/enrich.log   # Log to specific file
        """
    );
    
    parser.add_argument( '--dry-run', action='store_true',
                        help='Run without making database changes (default: False)' );
    parser.add_argument( '--batch-size', type=int, default=10,
                        help='Number of restaurants to process in this batch (default: 10)' );
    parser.add_argument( '--rate', type=float, default=8.0,
                        help='Rate limit in requests per second (default: 8.0)' );
    parser.add_argument( '--log-file', type=str,
                        default=f"logs/enrichment_{datetime.now().strftime('%Y%m%d')}.log",
                        help='Log file path (default: logs/enrichment_YYYYMMDD.log)' );
    
    args = parser.parse_args();
    
    # Set up logging
    logger = setup_logging( args.log_file );
    
    # Check dependencies
    if not MONGODB_AVAILABLE:
        logger.error( "MongoDB not available. Install with: pip install pymongo" );
        return False;
        
    if not SERVICES_AVAILABLE:
        logger.error( "Required services not available. Check Google Places client and utilities." );
        return False;
        
    # Get MongoDB URI
    mongodb_uri = os.getenv( 'mongodb_uri', '' );
    if not mongodb_uri:
        logger.error( "MongoDB URI not found. Set 'mongodb_uri' environment variable." );
        return False;
        
    # Initialize and run job
    job = EnrichmentJobRunner(
        mongodb_uri=mongodb_uri,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        rate_limit_rps=args.rate
    );
    
    try:
        logger.info( "="*60 );
        logger.info( "Starting Google Places Enrichment Job" );
        logger.info( "="*60 );
        
        # Connect to database
        if not job.connect_database():
            logger.error( "Database connection failed" );
            return False;
            
        # Initialize Google client
        if not job.initialize_google_client():
            logger.error( "Google Places client initialization failed" );
            return False;
            
        # Run enrichment batch
        success = job.run_enrichment_batch();
        
        # Print summary
        job.print_job_summary();
        
        if success:
            logger.info( "✅ Enrichment job completed successfully" );
        else:
            logger.error( "❌ Enrichment job completed with errors" );
            
        return success;
        
    except KeyboardInterrupt:
        logger.info( "Job interrupted by user" );
        return False;
    except Exception as e:
        logger.error( f"Job failed with error: {e}", exc_info=True );
        return False;
    finally:
        job.cleanup();

if __name__ == "__main__":
    success = main();
    sys.exit( 0 if success else 1 );
