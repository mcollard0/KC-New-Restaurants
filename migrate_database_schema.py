#!/usr/bin/env python3
"""
Database Schema Migration Script
Adds Google Places fields to existing restaurant documents and creates test data
"""

import os;
import sys;
import logging;
import random;
from datetime import datetime;
from typing import Dict, List, Optional, Any;

try:
    from pymongo import MongoClient;
    from pymongo.errors import ConnectionFailure;
    MONGODB_AVAILABLE = True;
except ImportError:
    print( "pymongo is not installed. Please install it using 'pip install pymongo'." );
    MONGODB_AVAILABLE = False;

logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s' );
logger = logging.getLogger( __name__ );

class DatabaseMigration:
    """Handles database schema migration for Google Places integration."""
    
    def __init__( self, mongodb_uri: str, database_name: str = "kansas_city", collection_name: str = "food_businesses" ):
        self.mongodb_uri = mongodb_uri;
        self.database_name = database_name;
        self.collection_name = collection_name;
        self.client = None;
        self.db = None;
        self.collection = None;
        
        # Sample data for testing
        self.sample_cuisines = [ 'American', 'Mexican', 'Italian', 'Chinese', 'Thai', 'Indian', 'Mediterranean', 'BBQ', 'Seafood', 'Pizza', 'Burgers' ];
        self.sample_keywords = [ 'great food', 'excellent service', 'cozy atmosphere', 'friendly staff', 'clean', 'good value', 'fast service', 'delicious', 'fresh ingredients' ];
        
    def connect( self ) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = MongoClient( self.mongodb_uri, serverSelectionTimeoutMS=5000 );
            self.client.admin.command( 'ping' );
            self.db = self.client[ self.database_name ];
            self.collection = self.db[ self.collection_name ];
            logger.info( f"Connected to MongoDB: {self.database_name}.{self.collection_name}" );
            return True;
        except Exception as e:
            logger.error( f"Failed to connect to MongoDB: {e}" );
            return False;
            
    def backup_collection( self ) -> bool:
        """Create a backup before migration."""
        try:
            timestamp = datetime.now().strftime( "%Y%m%d_%H%M%S" );
            backup_name = f"pre_migration_backup_{timestamp}";
            
            # Export to JSON for backup
            documents = list( self.collection.find() );
            backup_file = f"backups/{backup_name}.json";
            
            os.makedirs( "backups", exist_ok=True );
            
            import json;
            with open( backup_file, 'w', encoding='utf-8' ) as f:
                for doc in documents:
                    if '_id' in doc:
                        doc[ '_id' ] = str( doc[ '_id' ] );
                json.dump( documents, f, indent=2, default=str );
                
            logger.info( f"✅ Pre-migration backup created: {backup_file} ({len( documents )} documents)" );
            return True;
            
        except Exception as e:
            logger.error( f"Error creating backup: {e}" );
            return False;
            
    def add_google_places_indexes( self ) -> bool:
        """Add new indexes for Google Places fields."""
        try:
            # Index for google_place_id for fast lookups
            self.collection.create_index( [ ( "google_place_id", 1 ) ], sparse=True, background=True );
            
            # Compound index for location-based queries
            self.collection.create_index( [ ( "latitude", 1 ), ( "longitude", 1 ) ], sparse=True, background=True );
            
            # Text index for cuisine search
            self.collection.create_index( [ ( "cuisine_type", 1 ) ], sparse=True, background=True );
            
            # Index for places update timestamp
            self.collection.create_index( [ ( "places_last_updated", 1 ) ], sparse=True, background=True );
            
            logger.info( "✅ Added Google Places indexes" );
            return True;
            
        except Exception as e:
            logger.error( f"Error adding indexes: {e}" );
            return False;
            
    def generate_mock_google_data( self, restaurant: Dict ) -> Dict:
        """Generate mock Google Places data for testing."""
        
        # Mock basic data
        mock_data = {
            'google_place_id': f"ChIJ{random.randint(100000000, 999999999)}_{restaurant['business_name'][:5].replace(' ', '')}",
            'google_rating': round( random.uniform( 3.2, 4.8 ), 1 ),
            'google_review_count': random.randint( 15, 450 ),
            'price_level': random.randint( 1, 4 ),
            'latitude': round( 39.0997 + random.uniform( -0.1, 0.1 ), 6 ),  # KC area
            'longitude': round( -94.5786 + random.uniform( -0.1, 0.1 ), 6 ), # KC area
            'cuisine_type': random.choice( self.sample_cuisines ),
            'places_last_updated': datetime.now().isoformat()
        };
        
        # Mock amenities (random selection)
        amenities = {
            'outdoor_seating': random.choice( [ True, False, None ] ),
            'takeout_available': random.choice( [ True, False ] ),
            'delivery_available': random.choice( [ True, False, None ] ),
            'reservations_accepted': random.choice( [ True, False, None ] ),
            'wheelchair_accessible': random.choice( [ True, False ] ),
            'good_for_children': random.choice( [ True, False, None ] ),
            'serves_alcohol': random.choice( [ True, False, None ] ),
            'parking_available': random.choice( [ True, False, None ] )
        };
        
        # Only include non-null amenities
        for key, value in amenities.items():
            if value is not None:
                mock_data[ key ] = value;
                
        # Mock sentiment analysis
        positive_pct = random.randint( 40, 85 );
        negative_pct = random.randint( 5, 20 );
        neutral_pct = 100 - positive_pct - negative_pct;
        
        mock_data[ 'sentiment_avg' ] = round( random.uniform( 0.1, 0.8 ), 3 );
        mock_data[ 'sentiment_distribution' ] = {
            'positive': positive_pct,
            'neutral': neutral_pct,
            'negative': negative_pct
        };
        
        # Mock keywords
        mock_data[ 'review_keywords' ] = random.sample( self.sample_keywords, k=random.randint( 2, 4 ) );
        mock_data[ 'sentiment_summary' ] = f"Generally Positive (positive {positive_pct}%) - Key topics: {', '.join( mock_data[ 'review_keywords' ][:3] )}";
        
        # Mock business hours
        mock_data[ 'business_hours' ] = {
            'monday': '11:00-22:00',
            'tuesday': '11:00-22:00', 
            'wednesday': '11:00-22:00',
            'thursday': '11:00-22:00',
            'friday': '11:00-23:00',
            'saturday': '11:00-23:00',
            'sunday': '12:00-21:00'
        };
        
        mock_data[ 'review_summary' ] = f"Recent reviews highlight {mock_data['review_keywords'][0]} and {mock_data['review_keywords'][1]}. Average rating of {mock_data['google_rating']} stars from {mock_data['google_review_count']} reviews.";
        
        return mock_data;
        
    def migrate_documents( self, add_mock_data: bool = False, sample_size: int = 10 ) -> bool:
        """Migrate existing documents to new schema."""
        try:
            # Get restaurants without Google Places data
            query = {
                '$or': [
                    { 'google_place_id': { '$exists': False } },
                    { 'google_place_id': None },
                    { 'google_place_id': '' }
                ]
            };
            
            restaurants = list( self.collection.find( query ) );
            logger.info( f"Found {len( restaurants )} restaurants needing migration" );
            
            if not restaurants:
                logger.info( "No restaurants need migration" );
                return True;
                
            # Migrate documents
            migrated_count = 0;
            
            # Select sample for mock data if requested
            if add_mock_data:
                if len( restaurants ) > sample_size:
                    restaurants = random.sample( restaurants, sample_size );
                    logger.info( f"Adding mock data to {len( restaurants )} sample restaurants" );
                    
            for restaurant in restaurants:
                try:
                    update_data = {};
                    
                    if add_mock_data:
                        # Add mock Google Places data
                        update_data = self.generate_mock_google_data( restaurant );
                        logger.info( f"Adding mock data to: {restaurant.get( 'business_name', 'Unknown' )}" );
                    else:
                        # Just add placeholder fields
                        update_data = {
                            'google_place_id': None,
                            'google_rating': None,
                            'google_review_count': None,
                            'price_level': None,
                            'latitude': None,
                            'longitude': None,
                            'cuisine_type': None,
                            'places_last_updated': None
                        };
                        
                    # Update document
                    result = self.collection.update_one(
                        { '_id': restaurant[ '_id' ] },
                        { '$set': update_data }
                    );
                    
                    if result.modified_count > 0:
                        migrated_count += 1;
                        
                except Exception as e:
                    logger.error( f"Error migrating restaurant {restaurant.get( 'business_name', 'Unknown' )}: {e}" );
                    
            logger.info( f"✅ Migrated {migrated_count} documents" );
            return True;
            
        except Exception as e:
            logger.error( f"Error during migration: {e}" );
            return False;
            
    def verify_migration( self ) -> Dict:
        """Verify migration results."""
        try:
            # Count documents with Google Places data
            with_google = self.collection.count_documents( { 'google_place_id': { '$ne': None } } );
            without_google = self.collection.count_documents( { 
                '$or': [
                    { 'google_place_id': { '$exists': False } },
                    { 'google_place_id': None },
                    { 'google_place_id': '' }
                ]
            } );
            total = self.collection.count_documents( {} );
            
            # Sample document with Google data
            sample_doc = self.collection.find_one( { 'google_place_id': { '$ne': None } } );
            
            # Check indexes
            indexes = list( self.collection.list_indexes() );
            
            results = {
                'total_documents': total,
                'with_google_data': with_google,
                'without_google_data': without_google,
                'migration_percentage': round( (with_google / total) * 100, 1 ) if total > 0 else 0,
                'sample_document_fields': list( sample_doc.keys() ) if sample_doc else [],
                'indexes': [ idx[ 'name' ] for idx in indexes ]
            };
            
            return results;
            
        except Exception as e:
            logger.error( f"Error verifying migration: {e}" );
            return {};
            
    def print_migration_summary( self, results: Dict ):
        """Print migration summary report."""
        print( "\n" + "="*70 );
        print( "🏗️  Database Schema Migration Summary" );
        print( "="*70 );
        
        print( f"\n📊 Migration Results:" );
        print( f"   Total documents: {results.get( 'total_documents', 0 ):,}" );
        print( f"   With Google Places data: {results.get( 'with_google_data', 0 ):,}" );
        print( f"   Without Google Places data: {results.get( 'without_google_data', 0 ):,}" );
        print( f"   Migration completion: {results.get( 'migration_percentage', 0 )}%" );
        
        print( f"\n🗂️  Schema Fields ({len( results.get( 'sample_document_fields', [] ) )} total):" );
        fields = results.get( 'sample_document_fields', [] );
        google_fields = [ f for f in fields if f.startswith( 'google_' ) or f in [ 'latitude', 'longitude', 'cuisine_type', 'price_level' ] ];
        
        if google_fields:
            print( f"   Google Places fields: {', '.join( google_fields )}" );
        else:
            print( "   No Google Places fields found" );
            
        print( f"\n🔍 Database Indexes ({len( results.get( 'indexes', [] ) )} total):" );
        for idx in results.get( 'indexes', [] ):
            print( f"   • {idx}" );
            
        print( "\n" + "="*70 );
        
    def cleanup( self ):
        """Clean up database connection."""
        if self.client:
            self.client.close();
            logger.info( "Database connection closed" );

def main():
    """Main migration function."""
    import argparse;
    
    parser = argparse.ArgumentParser( description='Migrate database schema for Google Places integration' );
    parser.add_argument( '--add-mock-data', action='store_true', 
                        help='Add mock Google Places data to sample restaurants for testing' );
    parser.add_argument( '--sample-size', type=int, default=10,
                        help='Number of restaurants to add mock data to (default: 10)' );
    
    args = parser.parse_args();
    
    # Check dependencies
    if not MONGODB_AVAILABLE:
        logger.error( "MongoDB not available. Install pymongo." );
        return False;
        
    # Get MongoDB URI
    mongodb_uri = os.getenv( 'mongodb_uri', '' );
    if not mongodb_uri:
        logger.error( "MongoDB URI not found. Set 'mongodb_uri' environment variable." );
        return False;
        
    # Initialize migration
    migration = DatabaseMigration( mongodb_uri );
    
    try:
        # Connect to database
        if not migration.connect():
            return False;
            
        # Create backup
        logger.info( "Creating pre-migration backup..." );
        if not migration.backup_collection():
            logger.warning( "Backup failed, but continuing migration" );
            
        # Add indexes
        logger.info( "Adding Google Places indexes..." );
        if not migration.add_google_places_indexes():
            logger.error( "Failed to add indexes" );
            return False;
            
        # Migrate documents
        logger.info( "Migrating document schema..." );
        if not migration.migrate_documents( args.add_mock_data, args.sample_size ):
            logger.error( "Migration failed" );
            return False;
            
        # Verify results
        logger.info( "Verifying migration..." );
        results = migration.verify_migration();
        
        # Print summary
        migration.print_migration_summary( results );
        
        logger.info( "✅ Database migration completed successfully" );
        return True;
        
    except Exception as e:
        logger.error( f"Migration failed: {e}" );
        return False;
    finally:
        migration.cleanup();

if __name__ == "__main__":
    success = main();
    sys.exit( 0 if success else 1 );
