#!/usr/bin/env python3
"""
Database Status Check and Preparation Script
Analyzes current MongoDB database and prepares for Google Places integration
"""

import os;
import sys;
import logging;
import time;
from datetime import datetime;
from typing import Dict, List, Optional;

try:
    from pymongo import MongoClient;
    from pymongo.errors import ConnectionFailure;
    MONGODB_AVAILABLE = True;
except ImportError:
    print( "pymongo is not installed. Please install it using 'pip install pymongo'." );
    MONGODB_AVAILABLE = False;

logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s' );
logger = logging.getLogger( __name__ );

class DatabaseStatusChecker:
    def __init__( self, mongodb_uri: str = "", database_name: str = "kansas_city", collection_name: str = "food_businesses" ):
        self.mongodb_uri = mongodb_uri;
        self.database_name = database_name;
        self.collection_name = collection_name;
        self.client = None;
        self.db = None;
        self.collection = None;
        
    def connect( self ) -> bool:
        """Connect to MongoDB database."""
        if not self.mongodb_uri:
            logger.error( "MongoDB URI not provided" );
            return False;
            
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
            
    def analyze_current_schema( self ) -> Dict:
        """Analyze current database schema and structure."""
        if self.collection is None:
            logger.error( "Database not connected" );
            return {};
            
        try:
            # Get collection stats
            stats = self.db.command( "collStats", self.collection_name );
            
            # Sample documents to understand current schema
            sample_docs = list( self.collection.find().limit( 10 ) );
            
            # Get all unique fields across documents
            all_fields = set();
            field_types = {};
            
            for doc in sample_docs:
                for field, value in doc.items():
                    all_fields.add( field );
                    if field not in field_types:
                        field_types[ field ] = type( value ).__name__;
                        
            # Check indexes
            indexes = self.collection.list_indexes();
            index_info = [ idx for idx in indexes ];
            
            analysis = {
                'collection_stats': {
                    'document_count': stats.get( 'count', 0 ),
                    'size_bytes': stats.get( 'size', 0 ),
                    'avg_doc_size': stats.get( 'avgObjSize', 0 ),
                    'storage_size': stats.get( 'storageSize', 0 ),
                    'total_index_size': stats.get( 'totalIndexSize', 0 )
                },
                'schema_analysis': {
                    'unique_fields': sorted( list( all_fields ) ),
                    'field_types': field_types,
                    'sample_document': sample_docs[ 0 ] if sample_docs else None
                },
                'indexes': index_info,
                'google_places_ready': self._check_google_places_fields( sample_docs ),
                'migration_recommendations': self._get_migration_recommendations( sample_docs, all_fields )
            };
            
            return analysis;
            
        except Exception as e:
            logger.error( f"Error analyzing schema: {e}" );
            return {};
            
    def _check_google_places_fields( self, sample_docs: List[ Dict ] ) -> Dict:
        """Check if Google Places fields exist in current documents."""
        google_fields = [
            'google_place_id', 'google_rating', 'google_review_count', 'price_level',
            'latitude', 'longitude', 'cuisine_type', 'outdoor_seating', 'takeout_available',
            'delivery_available', 'reservations_accepted', 'wheelchair_accessible',
            'good_for_children', 'serves_alcohol', 'parking_available', 'business_hours',
            'review_summary', 'sentiment_avg', 'sentiment_distribution', 'review_keywords',
            'places_last_updated'
        ];
        
        field_presence = {};
        for field in google_fields:
            field_presence[ field ] = any( field in doc for doc in sample_docs );
            
        existing_count = sum( field_presence.values() );
        
        return {
            'fields_present': field_presence,
            'total_google_fields': len( google_fields ),
            'existing_google_fields': existing_count,
            'integration_status': 'complete' if existing_count == len( google_fields ) else 
                                 'partial' if existing_count > 0 else 'not_started'
        };
        
    def _get_migration_recommendations( self, sample_docs: List[ Dict ], all_fields: set ) -> List[ str ]:
        """Get recommendations for database migration."""
        recommendations = [];
        
        # Check basic KC fields
        required_kc_fields = [ 'business_name', 'dba_name', 'address', 'business_type', 'valid_license_for' ];
        missing_kc_fields = [ field for field in required_kc_fields if field not in all_fields ];
        
        if missing_kc_fields:
            recommendations.append( f"❌ Missing required KC fields: {', '.join( missing_kc_fields )}" );
        else:
            recommendations.append( "✅ All required KC fields present" );
            
        # Check Google Places integration
        google_present = any( 'google_' in field for field in all_fields );
        if not google_present:
            recommendations.append( "🔄 Ready for Google Places integration - no existing Google data found" );
        else:
            recommendations.append( "⚠️  Partial Google Places data detected - migration needed" );
            
        # Check document count
        doc_count = len( sample_docs );
        if doc_count > 0:
            recommendations.append( f"📊 Database has data ({doc_count} sample docs) - backup recommended before migration" );
        else:
            recommendations.append( "📝 Empty database - safe to create new schema" );
            
        return recommendations;
        
    def create_backup( self, backup_dir: str = "backups" ) -> bool:
        """Create a backup of current database."""
        if self.collection is None:
            logger.error( "Database not connected" );
            return False;
            
        try:
            # Create backup directory
            timestamp = datetime.now().strftime( "%Y%m%d_%H%M%S" );
            backup_path = os.path.join( backup_dir, f"mongodb_backup_{timestamp}" );
            os.makedirs( backup_path, exist_ok=True );
            
            # Export collection to JSON
            documents = list( self.collection.find() );
            backup_file = os.path.join( backup_path, f"{self.collection_name}_backup.json" );
            
            import json;
            with open( backup_file, 'w', encoding='utf-8' ) as f:
                # Convert ObjectId to string for JSON serialization
                for doc in documents:
                    if '_id' in doc:
                        doc[ '_id' ] = str( doc[ '_id' ] );
                json.dump( documents, f, indent=2, default=str );
                
            logger.info( f"✅ Backup created: {backup_file} ({len( documents )} documents)" );
            
            # Create metadata file
            metadata = {
                'backup_timestamp': timestamp,
                'database_name': self.database_name,
                'collection_name': self.collection_name,
                'document_count': len( documents ),
                'backup_file': backup_file
            };
            
            metadata_file = os.path.join( backup_path, "backup_metadata.json" );
            with open( metadata_file, 'w', encoding='utf-8' ) as f:
                json.dump( metadata, f, indent=2 );
                
            return True;
            
        except Exception as e:
            logger.error( f"Error creating backup: {e}" );
            return False;
            
    def print_status_report( self, analysis: Dict ):
        """Print a comprehensive status report."""
        print( "\n" + "="*80 );
        print( "🏪 KC New Restaurants - Database Status Report" );
        print( "="*80 );
        
        # Collection Stats
        stats = analysis.get( 'collection_stats', {} );
        print( f"\n📊 Collection Statistics:" );
        print( f"   Database: {self.database_name}" );
        print( f"   Collection: {self.collection_name}" );
        print( f"   Document Count: {stats.get( 'document_count', 0 ):,}" );
        print( f"   Storage Size: {stats.get( 'size_bytes', 0 ):,} bytes" );
        print( f"   Average Document Size: {stats.get( 'avg_doc_size', 0 ):,} bytes" );
        
        # Schema Analysis
        schema = analysis.get( 'schema_analysis', {} );
        fields = schema.get( 'unique_fields', [] );
        print( f"\n🗂️  Current Schema ({len( fields )} fields):" );
        for field in fields:
            field_type = schema.get( 'field_types', {} ).get( field, 'unknown' );
            print( f"   • {field}: {field_type}" );
            
        # Google Places Status
        google_status = analysis.get( 'google_places_ready', {} );
        integration_status = google_status.get( 'integration_status', 'unknown' );
        print( f"\n🌍 Google Places Integration Status: {integration_status.upper()}" );
        print( f"   Google Fields Present: {google_status.get( 'existing_google_fields', 0 )}/{google_status.get( 'total_google_fields', 0 )}" );
        
        # Recommendations
        recommendations = analysis.get( 'migration_recommendations', [] );
        print( f"\n💡 Migration Recommendations:" );
        for rec in recommendations:
            print( f"   {rec}" );
            
        # Indexes
        indexes = analysis.get( 'indexes', [] );
        print( f"\n🔍 Database Indexes ({len( indexes )}):" );
        for idx in indexes:
            print( f"   • {idx.get( 'name', 'unknown' )}: {idx.get( 'key', {} )}" );
            
        print( "\n" + "="*80 );

def main():
    """Main function to run database status check."""
    
    # Get MongoDB URI from environment or use default
    mongodb_uri = os.getenv( 'mongodb_uri', '' );
    if not mongodb_uri:
        logger.error( "MongoDB URI not found in environment variables" );
        logger.info( "Please set 'mongodb_uri' environment variable" );
        return False;
        
    # Initialize checker
    checker = DatabaseStatusChecker( mongodb_uri );
    
    # Connect to database
    if not checker.connect():
        return False;
        
    # Analyze current state
    logger.info( "Analyzing current database schema..." );
    analysis = checker.analyze_current_schema();
    
    if not analysis:
        logger.error( "Failed to analyze database" );
        return False;
        
    # Create backup before any changes
    logger.info( "Creating backup before analysis..." );
    backup_success = checker.create_backup();
    
    if backup_success:
        logger.info( "✅ Backup completed successfully" );
    else:
        logger.warning( "⚠️  Backup failed - proceed with caution" );
        
    # Print comprehensive report
    checker.print_status_report( analysis );
    
    # Close connection
    if checker.client:
        checker.client.close();
        
    return True;

if __name__ == "__main__":
    if not MONGODB_AVAILABLE:
        print( "MongoDB not available. Exiting." );
        sys.exit( 1 );
        
    success = main();
    sys.exit( 0 if success else 1 );
