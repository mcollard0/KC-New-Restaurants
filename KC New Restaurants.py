#/bin/python3
"""

KC New Restaurants Monitor
Automated food business license tracking system

1. Download the KC New Restaurants data from: https://city.kcmo.org/kc/BusinessLicenseSearch/Default
2. Iterate / Filters for current year and food businesses
3. Insert MongoDB with new records
4. Send HTML email alert for new business

"""

import requests;
import re;
import csv;
import time;
import smtplib;
import os;
import logging;
import urllib.parse;
import argparse;
import random;
import tempfile;
from datetime import datetime;
from email.mime.text import MIMEText;
from email.mime.multipart import MIMEMultipart;
from typing import List, Dict, Tuple, Optional;

try:
    from pymongo import MongoClient;
    from pymongo.errors import ConnectionFailure;
    MONGODB_AVAILABLE = True;
except ImportError:
    print( "pymongo is not installed. Please install it using 'pip install pymongo' or 'apt install python3-pymongo'." );
    MONGODB_AVAILABLE = False;

# Import dual database manager
try:
    from services.database_manager import DatabaseManager;
    DATABASE_MANAGER_AVAILABLE = True;
except ImportError as e:
    logger.warning( f"Database manager not available: {e}" );
    DATABASE_MANAGER_AVAILABLE = False;

# Initialize logger first
logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s' );
handlers = [ logging.FileHandler( "kc_new_restaurants.log" ), logging.StreamHandler() ];
logging.getLogger().handlers = handlers;
logger = logging.getLogger( __name__ );

# Import Google Places client for real-time enrichment
try:
    from services.google_places_client import GooglePlacesClient, PlaceData;
    GOOGLE_PLACES_AVAILABLE = True;
except ImportError as e:
    logger.warning( f"Google Places enrichment not available: {e}" );
    GOOGLE_PLACES_AVAILABLE = False;


#Distilled list of business types that are food related -- changed to just be restaurants and grocery stores
FOOD_BUSINESS_TYPES = frozenset( [
    "Supermarkets and Other Grocery Retailers (except Convenience Retailers)",
    #"Drinking Places (Alcoholic Beverages)",
    #"Convenience Retailers",
    "Retail Bakeries",
    "All Other Specialty Food Retailers", 
    #"Beer Wine and Liquor Retailers",
    "Food (Health) Supplement Retailers",
    "Mobile Food Services",
    #"Caterers",
    "Full-Service Restaurants",
    "Limited-Service Restaurants",
    #"Food Service Contractors",
    "Snack and Nonalcoholic Beverage Bars",
    #"Breweries",
    #"Meat Retailers",
    #"Distilleries",
    "Confectionery and Nut Retailers",
    #"Wineries", 
    "Cafeterias Grill Buffets and Buffets",
    #"Ice Cream and Frozen Dessert Manufacturing"
] );

class KCRestaurant:
    def __init__( self, mongodb_uri: str = "", database_name: str = "kc_new_restaurants", collection_name: str = "restaurants", dry_run: bool = False, enable_enrichment: bool = True ):
        self.mongodb_uri = mongodb_uri;
        self.database_name = database_name;
        self.collection_name = collection_name;
        self.dry_run = dry_run;
        self.enable_enrichment = enable_enrichment;
        self.session = self.db = self.collection = self.client = None;
        
        # Initialize dual database manager
        self.db_manager = None;

        self.stats = { 'total_records': 0, 'food_businesses': 0, 'current_year_food': 0, 'new_businesses':0,
    'existing_businesses':0, 'download_time':0, 'processing_time':0, 'enrichment_success': 0, 'enrichment_failed': 0 };

        self.new_businesses = [ ]; # new businesses found this run
        
        # Initialize Google Places client if available and enabled
        self.google_places_client = None;
        if GOOGLE_PLACES_AVAILABLE and self.enable_enrichment:
            logger.info( "Google Places enrichment will be enabled after MongoDB setup" );
        elif not self.enable_enrichment:
            logger.info( "Google Places enrichment disabled" );
        else:
            logger.warning( "Google Places enrichment not available" );

    def _sanitize_uri_for_logging(self, uri: str) -> str:
        """Sanitize MongoDB URI for logging by removing credentials."""
        if not uri:
            return "[empty]";
        try:
            # Remove credentials from URI for logging
            if '@' in uri:
                # Format: mongodb://username:password@host:port/db
                parts = uri.split('@');
                if len(parts) >= 2:
                    protocol_part = parts[0].split('://')[0] + '://';
                    host_part = '@'.join(parts[1:]);
                    return f"{protocol_part}[credentials_removed]@{host_part}";
            return uri;
        except Exception:
            return "[uri_parse_error]";

    def _sanitize_email_for_logging(self, email: str) -> str:
        """Sanitize email address for logging by masking part of it."""
        if not email or '@' not in email:
            return "[invalid_email]";
        try:
            local, domain = email.split('@', 1);
            # Show first 2 chars of local part, mask the rest
            masked_local = local[:2] + '*' * max(0, len(local) - 2);
            return f"{masked_local}@{domain}";
        except Exception:
            return "[email_parse_error]";

    def setup_mongodb( self ) -> bool:
        try:
            # Initialize dual database manager (MongoDB + SQLite)
            if DATABASE_MANAGER_AVAILABLE:
                self.db_manager = DatabaseManager(mongodb_uri=self.mongodb_uri);
                status = self.db_manager.get_status();
                logger.info( f"Database Manager Status: MongoDB {'✅' if status['mongodb']['available'] else '❌'}, SQLite {'✅' if status['sqlite']['available'] else '❌'}" );
                
                # Get collection for compatibility with existing code
                self.collection = self.db_manager.get_collection();
                
                if not status['mongodb']['available'] and not status['sqlite']['available']:
                    logger.error( "Neither MongoDB nor SQLite is available" );
                    return False;
                    
            else:
                # Fallback to direct MongoDB connection
                self.client = MongoClient( self.mongodb_uri, serverSelectionTimeoutMS=2500 );
                self.client.admin.command( 'ping' );
                self.client.admin.command( 'ismaster' );
                # Sanitize URI for logging (remove credentials if present)
                sanitized_uri = self._sanitize_uri_for_logging(self.mongodb_uri)
                logger.info( f"Connected to MongoDB: {sanitized_uri}" );
                self.db = self.client[ self.database_name ];
                self.collection = self.db[ self.collection_name ];

                # Drop old indexes if they exist to prevent conflicts
                if self.dry_run:
                    logger.info( "[DRY-RUN] Skipping drop_index operation for business_name_1" );
                else:
                    try:
                        self.collection.drop_index( "business_name_1" );
                        logger.info( "Dropped old business_name_1 index" );
                    except:
                        pass;  # Index may not exist
                
                # Create a compound unique index on business_name + address + business_type for franchise support
                if self.dry_run:
                    logger.info( "[DRY-RUN] Skipping index creation for compound business fields" );
                    logger.info( "[DRY-RUN] Skipping index creation for insert_date" );
                else:
                    self.collection.create_index( [ ( "business_name", 1 ), ( "address", 1 ), ( "business_type", 1 ) ], unique=True, background=True );
                    self.collection.create_index( [ ( "insert_date", 1 ) ], background=True );

            logger.info( f"Setup database: {self.database_name}, collection: {self.collection_name}" );
            
            # Initialize Google Places client after database setup
            if GOOGLE_PLACES_AVAILABLE and self.enable_enrichment and not self.google_places_client:
                try:
                    self.google_places_client = GooglePlacesClient(
                        mongodb_collection=self.collection
                    );
                    logger.info( "Google Places enrichment enabled with AI predictions" );
                except Exception as e:
                    logger.warning( f"Could not initialize Google Places client: {e}" );
            
            return True;

        except Exception as e:
            logging.error( f"Error setting up database: {e}" );
            return False;
    
    def flush_database( self ) -> bool:
        """Flush (truncate) the entire collection to start fresh."""
        if self.dry_run:
            logger.info( "[DRY-RUN] flush_database() skipped - would have deleted all documents in collection" );
            return True;
            
        if self.collection is None:
            logger.error( "MongoDB collection not initialized" );
            return False;
            
        try:
            # Get count before deletion for logging
            before_count = self.collection.count_documents( { } );
            
            # Delete all documents in the collection
            result = self.collection.delete_many( { } );
            
            logger.info( f"Flushed database collection '{self.collection_name}'" );
            logger.info( f"Deleted {result.deleted_count:,} documents (was {before_count:,} total)" );
            
            return True;
            
        except Exception as e:
            logger.error( f"Error flushing database collection: {e}" );
            return False;

    def download_kc_business_csv( self ) -> List[ List[ str ] ]:
        logger.info( "Downloading KC business license data..." );
        download_start = time.perf_counter();

        try:
            self.session = requests.Session();
            self.session.headers.update( {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            } );
            
            # Use the same approach as the working script
            url = "https://city.kcmo.org/kc/BusinessLicenseSearch/";
            
            logger.info( "  Getting initial search form..." );
            response = self.session.get( url );
            response.raise_for_status();
            
            # Extract form fields
            viewstate_match = re.search( r'__VIEWSTATE.*?value="([^"]*)"', response.text );
            generator_match = re.search( r'__VIEWSTATEGENERATOR.*?value="([^"]*)"', response.text );
            validation_match = re.search( r'__EVENTVALIDATION.*?value="([^"]*)"', response.text );
            
            if not all( [ viewstate_match, generator_match, validation_match ] ):
                logger.error( "Failed to extract necessary form fields from the initial page" );
                return [ ];
            
            logger.info( "  Submitting search form..." );
            form_data = {
                '__VIEWSTATE': viewstate_match.group( 1 ),
                '__VIEWSTATEGENERATOR': generator_match.group( 1 ),
                '__EVENTVALIDATION': validation_match.group( 1 ),
                'ctl00$MainContent$businessName': '',
                'ctl00$MainContent$dbaName': '',
                'ctl00$MainContent$address': '',
                'ctl00$MainContent$businessType': '',
                'ctl00$MainContent$expirationDate': '',
                'ctl00$MainContent$searchBtn': 'Begin Search'
            };
            
            response = self.session.post( url, data=form_data );
            response.raise_for_status();
            
            # Now we should have the search results page - look for export button
            logger.info( "  Looking for CSV export button..." );
            
            # Look for export button in various common patterns
            export_patterns = [
                r'<input[^>]*value="[^"]*Export[^"]*Data[^"]*"[^>]*name="([^"]+)"',
                r'<input[^>]*name="([^"]+)"[^>]*value="[^"]*Export[^"]*Data[^"]*"',
                r'<input[^>]*value="[^"]*Export[^"]*CSV[^"]*"[^>]*name="([^"]+)"',
                r'<input[^>]*name="([^"]+)"[^>]*value="[^"]*Export[^"]*CSV[^"]*"',
                r'href="([^"]*ExportToCSV[^"]*)"',
                r'<a[^>]*href="([^"]*export[^"]*csv[^"]*)"',
                r'onclick="[^"]*export[^"]*csv[^"]*"[^>]*name="([^"]+)"'
            ];
            
            export_button_name = None;
            export_url = None;
            
            for pattern in export_patterns:
                match = re.search( pattern, response.text, re.IGNORECASE );
                if match:
                    if 'href=' in pattern:
                        export_url = match.group( 1 );
                        logger.info( f"  Found export URL: {export_url}" );
                    else:
                        export_button_name = match.group( 1 );
                        logger.info( f"  Found export button: {export_button_name}" );
                    break;
            
            if export_url:
                # It's a direct link
                if not export_url.startswith( 'http' ):
                    export_url = urllib.parse.urljoin( url, export_url );
                logger.info( "  Downloading CSV via export URL..." );
                response = self.session.get( export_url );
                response.raise_for_status();
            elif export_button_name:
                # It's a form button - need to submit form again with export button
                logger.info( "  Submitting export form..." );
                
                # Extract updated form fields from results page
                viewstate_match = re.search( r'__VIEWSTATE.*?value="([^"]*)"', response.text );
                generator_match = re.search( r'__VIEWSTATEGENERATOR.*?value="([^"]*)"', response.text );
                validation_match = re.search( r'__EVENTVALIDATION.*?value="([^"]*)"', response.text );
                
                if not all( [ viewstate_match, generator_match, validation_match ] ):
                    logger.error( "Failed to extract form fields from results page" );
                    return [ ];
                
                export_form_data = {
                    '__VIEWSTATE': viewstate_match.group( 1 ),
                    '__VIEWSTATEGENERATOR': generator_match.group( 1 ),
                    '__EVENTVALIDATION': validation_match.group( 1 ),
                    export_button_name: 'Export to CSV'
                };
                
                response = self.session.post( url, data=export_form_data );
                response.raise_for_status();
            else:
                logger.error( "Could not find CSV export button or link" );
                logger.info( f"Response preview: {response.text[:1000]}" );
                
                # Save full response for debugging in a temporary file
                try:
                    with tempfile.NamedTemporaryFile( mode='w', suffix='_debug_response.html', delete=False, encoding='utf-8' ) as f:
                        f.write( response.text );
                        debug_file = f.name;
                    logger.info( f"Saved full response to {debug_file} for analysis" );
                except Exception as e:
                    logger.warning( f"Could not save debug file: {e}" );
                
                # Look for any forms or buttons that might be relevant
                forms = re.findall( r'<form[^>]*>.*?</form>', response.text, re.DOTALL | re.IGNORECASE );
                logger.info( f"Found {len(forms)} form(s) in response" );
                
                buttons = re.findall( r'<(?:input|button)[^>]*(?:type=["\']?(?:submit|button)["\']?|value=["\'][^"\'>]*(?:export|csv|download)[^"\'>]*["\'])[^>]*>', response.text, re.IGNORECASE );
                logger.info( f"Found potential buttons: {buttons}" );
                
                return [ ];

            #parsing
            csv_text = response.text;
            csv_lines = csv_text.splitlines();
            reader = csv.reader( csv_lines );
            rows = list( reader );
            
            self.stats[ 'download_time' ] = time.perf_counter() - download_start;

            # Debug: Print first few lines to see what we got
            logger.info( f"Response content type: {response.headers.get('content-type', 'unknown')}" );
            logger.info( f"Response status: {response.status_code}" );
            logger.info( f"First 500 chars of response: {csv_text[:500]}" );
            logger.info( f"Number of lines in response: {len(csv_lines)}" );
            if rows:
                logger.info( f"First row (header): {rows[0] if rows else 'None'}" );
                logger.info( f"Second row (sample): {rows[1] if len(rows) > 1 else 'None'}" );

            if rows and len( rows ) > 1:
                self.stats[ 'total_records' ] = len( rows ) - 1;
                logger.info( f"Downloaded {self.stats['total_records']} records from KC Business License data in {self.stats['download_time']:.2f} seconds" );
                return rows;

            logger.warning( "No data found in downloaded CSV" );
            return [ ];

        except Exception as e:
            logger.error( f"Error downloading KC Business License data: {e}" );
            return [ ];

    def is_food_business( self, business_type: str ) -> bool:
        return business_type.strip().strip( '"' ) in FOOD_BUSINESS_TYPES;
    
    def enrich_restaurant_data( self, document: dict ) -> dict:
        """Enrich restaurant document with Google Places data if available."""
        if not self.google_places_client or not self.enable_enrichment:
            return document;
        
        business_name = document.get( 'business_name', '' );
        dba_name = document.get( 'dba_name', '' );
        address = document.get( 'address', '' );
        
        # Use DBA name if available, otherwise business name
        search_name = dba_name.strip() if dba_name.strip() else business_name.strip();
        
        if not search_name or not address:
            logger.debug( f"Skipping enrichment - missing name or address: {search_name} at {address}" );
            return document;
        
        try:
            logger.debug( f"Enriching data for: {search_name} at {address}" );
            
            # Search for the place and get enriched data
            place_data = self.google_places_client.enrich_restaurant_data( search_name, address );
            
            if place_data:
                # Add Google Places data to document
                document.update( {
                    'google_place_id': place_data.place_id,
                    'google_rating': place_data.rating,
                    'google_user_ratings_total': place_data.user_ratings_total,
                    'google_formatted_address': place_data.formatted_address,
                    'google_name': place_data.name,
                    'cuisine_type': place_data.cuisine_type,
                    'price_level': place_data.price_level,
                    'latitude': place_data.latitude,
                    'longitude': place_data.longitude,
                    'outdoor_seating': place_data.outdoor_seating,
                    'takeout_available': place_data.takeout_available,
                    'delivery_available': place_data.delivery_available,
                    'reservations_accepted': place_data.reservations_accepted,
                    'wheelchair_accessible': place_data.wheelchair_accessible,
                    'good_for_children': place_data.good_for_children,
                    'serves_alcohol': place_data.serves_alcohol,
                    'parking_available': place_data.parking_available,
                    'business_hours': place_data.business_hours,
                    'sentiment_distribution': place_data.sentiment_distribution,
                    'sentiment_summary': place_data.sentiment_summary,
                    'sentiment_avg': place_data.sentiment_avg,
                    'review_keywords': place_data.review_keywords,
                    'review_summary': place_data.review_summary,
                    'enriched_date': time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() ),
                    'api_fields_retrieved': place_data.api_fields_retrieved,
                    'last_updated': place_data.last_updated
                } );
                
                self.stats['enrichment_success'] += 1;
                logger.debug( f"Successfully enriched {search_name} - Rating: {place_data.rating}, Cuisine: {place_data.cuisine_type}" );
            else:
                self.stats['enrichment_failed'] += 1;
                logger.debug( f"No Google Places data found for: {search_name} at {address}" );
                    
        except Exception as e:
            self.stats['enrichment_failed'] += 1;
            logger.warning( f"Failed to enrich {search_name}: {e}" );
            
        return document;

    def exists( self, business_name: str, address: str=None, business_type: str=None ) -> bool:
        """Check if a business already exists in the database based on name, address, and business type."""
        if self.collection is None: 
            return False;
        
        # Build query filter - all three fields must match for a duplicate
        query_filter = {
            "business_name": business_name,
            "address": address,
            "business_type": business_type
        };

        try: 
            logging.debug( f"Checking if exists: {business_name} at {address} ({business_type})" );
            existing_count = self.collection.count_documents( query_filter, limit=1 );
            return existing_count > 0;
        except Exception as e:
            logging.error( f"Error checking restaurant in DB: {e}" );
            return False;

    def process( self, csv_rows: List[ List[ str ] ] ) -> bool: 
        if not csv_rows or len( csv_rows ) < 2:
            logger.warning( "No data to process" );
            return False;

        processing_start = time.perf_counter();
        current_year = time.localtime().tm_year;
        header = csv_rows[ 0 ];
        expected_header = [ 'Business Name', 'DBA Name', 'Address', 'Business Type', 'Valid License For' ];
        
        if header != expected_header:
            logger.error( f"Unexpected CSV header. Expected: {expected_header}, Found: {header}" );
            return False;

        logger.info( f"Processing business license data..." );
        logger.info( f" Processing {len(csv_rows)-1:,} records..." );
        
        mongodb_not_initialized_warned = False;
        
        for row in csv_rows[ 1: ]:
            if len( row ) < 5:
                logger.warning( f"Skipping malformed row: {row}" );
                continue;

            business_name = row[ 0 ].strip().strip( '"' );
            dba_name = row[ 1 ].strip().strip( '"' );
            address = row[ 2 ].strip().strip( '"' );
            business_type = row[ 3 ].strip().strip( '"' );
            valid_license_for = row[ 4 ].strip().strip( '"' );  # This is the year

            if not self.is_food_business( business_type ): 
                continue;

            self.stats[ 'food_businesses' ] += 1;

            try:
                license_year = int( valid_license_for );
                if license_year != current_year: 
                    continue;
            except ( ValueError, TypeError ):
                logger.warning( f"Skipping row with invalid license year: {valid_license_for} for {business_name}" );
                continue;
            
            self.stats[ 'current_year_food' ] += 1;

            if self.exists( business_name, address, business_type ):
                self.stats[ 'existing_businesses' ] += 1;
                continue;
            
            # Create document for new business
            document = {
                "business_name": business_name,
                "dba_name": dba_name,
                "address": address,
                "business_type": business_type,
                "valid_license_for": valid_license_for,
                "insert_date": time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() ),
                "deleted": False
            };
            
            # Enrich document with Google Places data before inserting
            try:
                enriched_document = self.enrich_restaurant_data( document.copy() );
            except Exception as e:
                logger.warning( f"Enrichment failed for {business_name}, proceeding with basic data: {e}" );
                enriched_document = document.copy();
            
            # Insert into database (dual storage: MongoDB + SQLite)
            if self.db_manager or self.collection is not None:
                if self.dry_run:
                    logger.info( f"[DRY-RUN] Skipping database insert for new business: {business_name}, {address}, {business_type}" );
                else:
                    try:
                        if self.db_manager:
                            # Use dual database manager (preferred)
                            success = self.db_manager.insert_document( enriched_document.copy() );
                            if success:
                                logger.debug( f"Inserted new business into dual database: {business_name}, {address}, {business_type}" );
                            else:
                                logger.error( f"Failed to insert new business into database: {business_name}" );
                        else:
                            # Fallback to direct MongoDB insertion
                            self.collection.insert_one( enriched_document.copy() );
                            logger.debug( f"Inserted new business into MongoDB: {business_name}, {address}, {business_type}" );
                    except Exception as e:
                        logger.error( f"Error inserting new business into database: {e}" );
            else:
                if not mongodb_not_initialized_warned:
                    logger.warning( "Database not initialized - running in no-persistence mode" );
                    mongodb_not_initialized_warned = True;

            self.stats[ 'new_businesses' ] += 1;
            # Use enriched document for email display to include Google Places data
            new_business = enriched_document.copy();
            new_business.pop( 'insert_date' );
            new_business.pop( 'deleted', None );
            self.new_businesses.append( new_business );

        self.stats[ 'processing_time' ] = time.perf_counter() - processing_start;
        
        # Log enrichment statistics if enrichment was enabled
        if self.enable_enrichment and ( self.stats['enrichment_success'] > 0 or self.stats['enrichment_failed'] > 0 ):
            logger.info( f"Google Places enrichment: {self.stats['enrichment_success']} successful, {self.stats['enrichment_failed']} failed" );
        
        logger.info( f"Processed {self.stats['total_records']} total records, found {self.stats['food_businesses']} food businesses in {self.stats['processing_time']:.2f} seconds" );

        return True;
    
    def _convert_price_level_for_display( self, price_level ) -> Optional[int]:
        """Convert price level to integer for display purposes.
        
        Handles both string constants and integers for backward compatibility.
        
        Args:
            price_level: Either integer (0-4) or string constant (PRICE_LEVEL_INEXPENSIVE, etc.)
            
        Returns:
            Integer price level (1-4) for display or None if invalid
        """
        if price_level is None:
            return None;
            
        # Handle integer format (existing data)
        if isinstance( price_level, int ):
            return price_level if 1 <= price_level <= 4 else None;
            
        # Handle string constants from Google Places API
        if isinstance( price_level, str ):
            price_level_mapping = {
                'PRICE_LEVEL_FREE': None,  # Don't show price level for free
                'PRICE_LEVEL_INEXPENSIVE': 1,
                'PRICE_LEVEL_MODERATE': 2,
                'PRICE_LEVEL_EXPENSIVE': 3,
                'PRICE_LEVEL_VERY_EXPENSIVE': 4
            };
            return price_level_mapping.get( price_level );
            
        return None;
        
    def generate_email_html( self ) -> str:
        if not self.new_businesses:
            return "<p>No new food businesses found this run.</p>";

        current_time = datetime.now().strftime( '%Y-%m-%d %H:%M:%S' );
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                h2 {{ color: #2c5aa0; text-align: center; margin-bottom: 30px; }}
                .summary {{ background-color: #e8f4fd; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
                .restaurant-table {{ width: 100%; margin-top: 20px; border-collapse: separate; border-spacing: 0; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .restaurant-row {{ background-color: white; }}
                .restaurant-row:nth-child(even) {{ background-color: #f9f9f9; }}
                .restaurant-row:hover {{ background-color: #e3f2fd; transition: background-color 0.3s; }}
                .restaurant-info {{ padding: 20px; vertical-align: top; width: 60%; }}
                .rating-cell {{ padding: 20px; text-align: center; vertical-align: middle; width: 40%; background-color: #fafafa; }}
                .restaurant-name {{ font-size: 18px; font-weight: bold; color: #1a73e8; text-decoration: none; }}
                .restaurant-name:hover {{ text-decoration: underline; }}
                .restaurant-address {{ color: #666; margin: 8px 0; font-size: 14px; }}
                .restaurant-details {{ color: #444; font-size: 14px; margin: 4px 0; }}
                .amenities {{ margin: 8px 0; }}
                .amenity-tag {{ display: inline-block; background-color: #e3f2fd; color: #1976d2; padding: 2px 6px; border-radius: 12px; font-size: 12px; margin: 2px; }}
                .sentiment-badge {{ display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 13px; font-weight: bold; margin: 4px 2px; }}
                .sentiment-positive {{ background-color: #e8f5e8; color: #2e7d32; }}
                .sentiment-mixed {{ background-color: #fff3e0; color: #f57c00; }}
                .sentiment-negative {{ background-color: #ffebee; color: #d32f2f; }}
                .sentiment-pending {{ background-color: #f5f5f5; color: #666; }}
                .keyword-tag {{ display: inline-block; background-color: #f3e5f5; color: #7b1fa2; padding: 2px 6px; border-radius: 8px; font-size: 11px; margin: 1px; }}
                .ai-rating {{ font-size: 48px; font-weight: bold; color: #2e7d32; margin: 0; line-height: 1; }}
                .ai-grade {{ font-size: 36px; font-weight: bold; margin: 5px 0; line-height: 1; }}
                .ai-confidence {{ font-size: 10px; color: #888; margin: 2px 0; font-weight: normal; }}
                .ai-label {{ font-size: 12px; color: #666; margin-top: 8px; }}
                .grade-a {{ color: #00a86b; }}
                .grade-b {{ color: #32cd32; }}
                .grade-c {{ color: #ffa500; }}
                .grade-d {{ color: #dc143c; }}
                .grade-f {{ color: #8b0000; }}
                .no-prediction {{ color: #999; font-style: italic; }}
                .google-data {{ font-size: 13px; color: #555; margin-top: 8px; }}
                .price-level {{ color: #2e7d32; font-weight: bold; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }}
                @media (max-width: 600px) {{
                    .container {{ margin: 10px; padding: 15px; }}
                    .restaurant-info, .rating-cell {{ display: block; width: 100%; }}
                    .ai-rating {{ font-size: 36px; }}
                    .ai-grade {{ font-size: 28px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🍽️ KC New Restaurants Alert</h2>
                
                <div class="summary">
                    <strong>Summary for {current_time}:</strong>
                    <ul>
                        <li>Total records processed: {self.stats['total_records']:,}</li>
                        <li>Food businesses found: {self.stats['food_businesses']:,}</li>
                        <li>Current year food businesses: {self.stats['current_year_food']:,}</li>
                        <li><strong>New businesses added: {len(self.new_businesses):,}</strong></li>
                        <li>Existing businesses (no change): {self.stats['existing_businesses']:,}</li>
                    </ul>
                </div>
                
                <h3>✨ New Food Businesses ({len(self.new_businesses)} found):</h3>
                
                <table class="restaurant-table">
        """;

        for food in self.new_businesses:
            friendly_name = food.get( 'dba_name', '' ).strip() + ' (' + food.get( 'business_name', '' ).strip() + ')' if food.get( 'dba_name', '' ).strip() else food.get( 'business_name', '' ).strip();
            google_link = f"https://www.google.com/search?q="+ urllib.parse.quote_plus( friendly_name + " " + food.get('address', '') ) +"";
            
            # Extract Google Places data if available
            google_rating = food.get( 'google_rating' );
            cuisine_type = food.get( 'cuisine_type', '' );
            price_level = food.get( 'price_level' );
            
            # Extract AI predictions if available
            ai_rating = food.get( 'ai_predicted_rating' );
            ai_grade = food.get( 'ai_predicted_grade', '' );
            ai_confidence_pct = food.get( 'ai_confidence_percentage' );
            ai_confidence_level = food.get( 'ai_confidence_level' );
            
            # Extract sentiment analysis data if available
            sentiment_distribution = food.get( 'sentiment_distribution', {} );
            review_keywords = food.get( 'review_keywords', [] );
            sentiment_summary = food.get( 'sentiment_summary', '' );
            
            # Build amenities list
            amenities = [];
            if food.get( 'outdoor_seating' ): amenities.append( '🌤️ Outdoor' );
            if food.get( 'takeout_available' ): amenities.append( '🥡 Takeout' );
            if food.get( 'delivery_available' ): amenities.append( '🚚 Delivery' );
            if food.get( 'wheelchair_accessible' ): amenities.append( '♿ Accessible' );
            if food.get( 'good_for_children' ): amenities.append( '👶 Kid-Friendly' );
            if food.get( 'serves_alcohol' ): amenities.append( '🍺 Alcohol' );
            
            amenities_html = ''.join( f'<span class="amenity-tag">{amenity}</span>' for amenity in amenities );
            
            # Format price level
            price_display = '';
            converted_price_level = self._convert_price_level_for_display( price_level );
            if converted_price_level is not None:
                dollar_signs = '$' * max( 1, converted_price_level );
                price_display = f'<span class="price-level">{dollar_signs}</span>';
            
            # Determine grade color class
            grade_class = 'no-prediction';
            if ai_grade:
                if ai_grade.startswith( 'A' ): grade_class = 'grade-a';
                elif ai_grade.startswith( 'B' ): grade_class = 'grade-b';
                elif ai_grade.startswith( 'C' ): grade_class = 'grade-c';
                elif ai_grade.startswith( 'D' ): grade_class = 'grade-d';
                elif ai_grade.startswith( 'F' ): grade_class = 'grade-f';
            
            # Build sentiment badge display
            sentiment_badge_html = '';
            if sentiment_distribution and sum( sentiment_distribution.values() ) > 0:
                positive_pct = sentiment_distribution.get( 'positive', 0 );
                negative_pct = sentiment_distribution.get( 'negative', 0 );
                
                if positive_pct >= 60:
                    sentiment_badge_html = f'<span class="sentiment-badge sentiment-positive">😊 Positive Reviews ({positive_pct}%)</span>';
                elif negative_pct >= 60:
                    sentiment_badge_html = f'<span class="sentiment-badge sentiment-negative">😞 Negative Reviews ({negative_pct}%)</span>';
                else:
                    sentiment_badge_html = f'<span class="sentiment-badge sentiment-mixed">😐 Mixed Reviews ({positive_pct}% pos)</span>';
            
            # Build keyword tags
            keywords_html = '';
            if review_keywords:
                keyword_tags = ''.join( f'<span class="keyword-tag">{keyword}</span>' for keyword in review_keywords[:3] );
                keywords_html = f'<div class="keywords">{keyword_tags}</div>';
            
            # Build Google data display
            google_info = [];
            if google_rating: google_info.append( f'Google: {google_rating}★' );
            if price_display: google_info.append( price_display );
            google_data_html = ' | '.join( google_info ) if google_info else '';
            
            html += f"""
                    <tr class="restaurant-row">
                        <td class="restaurant-info">
                            <a href="{google_link}" class="restaurant-name">{friendly_name}</a>
                            <div class="restaurant-address">{food.get('address', '')}</div>
                            <div class="restaurant-details">
                                <strong>{food.get('business_type', '')}</strong>
                                {(' | ' + cuisine_type) if cuisine_type else ''}
                            </div>
                            {('<div class="amenities">' + amenities_html + '</div>') if amenities else ''}
                            {sentiment_badge_html}
                            {keywords_html}
                            {('<div class="google-data">' + google_data_html + '</div>') if google_data_html else ''}
                        </td>
                        <td class="rating-cell">
            """;
            
            if ai_rating and ai_grade:
                # Build confidence display
                confidence_html = '';
                if ai_confidence_pct is not None:
                    confidence_html = f'<div class="ai-confidence">{ai_confidence_pct}% confidence</div>';
                
                html += f"""
                            <div class="ai-rating">{ai_rating:.1f}</div>
                            <div class="ai-grade {grade_class}">{ai_grade}</div>
                            {confidence_html}
                            <div class="ai-label">AI Predicted</div>
                """;
            else:
                html += f"""
                            <div class="no-prediction">Rating<br>Pending</div>
                            <div class="ai-label">Analysis in progress</div>
                """;
            
            html += """
                        </td>
                    </tr>
            """;

        html += f"""
                </table>
                
                <div class="footer">
                    <p><strong>Report generated:</strong> {current_time}</p>
                    <p><strong>Processing time:</strong> {self.stats['processing_time']:.2f}s | <strong>Download time:</strong> {self.stats['download_time']:.2f}s</p>
                    <p>🔍 Click restaurant names to search on Google | 🤖 AI ratings are predictive and for reference only</p>
                    <p><small>Grade Scale: A+ (4.6+) | A (4.4+) | B+ (4.0+) | C+ (3.4+) | D (2.5+) | F (&lt;2.5)</small></p>
                </div>
            </div>
        </body>
        </html>
        """;

        return html;

    def send_email_alert( self, 
                        smtp_server: str = "smtp.gmail.com",
                        smtp_port: int = 587,
                        sender_email: str = "",
                        sender_password: str = "",
                        recipient_email: str = "",
                        subject: str = None ) -> bool:
        
        if not all( [ sender_email, sender_password, recipient_email ] ):
            logger.error( "Email credentials or recipient not provided." );
            return False;   

        try:
            html = self.generate_email_html();
            msg = MIMEMultipart( 'alternative' );
            msg[ 'From' ] = sender_email;
            msg[ 'To' ] = recipient_email;
            msg[ 'Subject' ] = subject if subject else f"KC New Restaurants Alert - {len( self.new_businesses )} New Businesses Found";   

            html_part = MIMEText( html, 'html' );
            msg.attach( html_part );
            logger.info( f"Connecting to SMTP server {smtp_server}:{smtp_port}" );

            with smtplib.SMTP( smtp_server, smtp_port ) as server:
                server.starttls();
                server.login( sender_email, sender_password );
                server.sendmail( sender_email, recipient_email, msg.as_string() );
                # Sanitize email for logging
                sanitized_email = self._sanitize_email_for_logging(recipient_email)
                logger.info( f"Email sent to {sanitized_email}" );
                return True;

        
        except Exception as e:
            logger.error( f"Error sending email: {e}" );
            return False;
        
    def run( self ) -> bool:
        try:
            logger.info( "Starting KC New Restaurants processing" );
            start_time = time.perf_counter();  

            csv_rows = self.download_kc_business_csv();
            if not csv_rows:
                logger.error( "No data downloaded, exiting" );
                return False;   
            if not self.process( csv_rows ):
                logger.error( "Error processing data, exiting" );
                return False;
            

            print( "\n" + "="*60 );
            print( "KC FOOD BUSINESS MONITOR RESULTS" );
            print( "="*60 );
            print( f"Statistics:" );
            print( f"   Total records processed: {self.stats['total_records']:,}" );
            print( f"   Food businesses found: {self.stats['food_businesses']:,}" );
            print( f"   New businesses added: {self.stats['new_businesses']:,}" );
            print( f"   Existing businesses: {self.stats['existing_businesses']:,}" );
            
            # Display enrichment statistics if enabled
            if self.enable_enrichment and ( self.stats['enrichment_success'] > 0 or self.stats['enrichment_failed'] > 0 ):
                print( f"   Google Places enriched: {self.stats['enrichment_success']:,} successful, {self.stats['enrichment_failed']:,} failed" );
            elif self.enable_enrichment:
                print( f"   Google Places enrichment: enabled but no new businesses to enrich" );
            else:
                print( f"   Google Places enrichment: disabled" );
                
            total_time = time.perf_counter() - start_time;
            print( f"   Total processing time: {total_time:.2f}s" );
            
            print( f"\nNew Food Businesses Found ({len(self.new_businesses)}):" );

            if not self.new_businesses:
                print( "   No new food businesses found this run." );
                return False;
            else:   
                for food in self.new_businesses:
                    friendly_name = food.get( 'dba_name', '' ).strip() + ' (' + food.get( 'business_name', '' ).strip() + ')' if food.get( 'dba_name', '' ).strip() else food.get( 'business_name', '' ).strip();
                    print( f" - {friendly_name} {food['address']} {food['business_type']} (License: {food['valid_license_for']})" );
                print( "\n" + "="*60 + "\n" );
                return True;
        except Exception as e:      
            logger.error( f"Error in run method: {e}" );
            return False;

def is_running_under_cron():
    """Detect if the script is being run by cron."""
    # Check for common cron indicators
    cron_indicators = [
        os.getenv( 'CRON' ) is not None,  
        os.getenv( 'TERM' ) is None,      
        os.getenv( 'HOME' ) == '/var/spool/cron',  
        not os.isatty( 0 ),               
        os.getppid() == 1               
    ];
    
    minimal_env = len( [ k for k in os.environ.keys() if not k.startswith( '_' ) ] ) < 10;
    
    return any( cron_indicators ) or minimal_env;

def apply_random_delay( skip_delay=False ):
    """Apply a random delay of 1-15 minutes if running under cron (unless skipped)."""
    if skip_delay:
        logger.info( "Skipping random delay due to --nodelay option" );
        return;
        
    if is_running_under_cron():
        delay_minutes = random.randint( 1, 15 );
        delay_seconds = delay_minutes * 60;
        logger.info( f"Detected cron execution - applying random delay of {delay_minutes} minutes ({delay_seconds} seconds)" );
        logger.info( f"   This helps distribute server load. Use --nodelay to skip this delay." );
        time.sleep( delay_seconds );
        logger.info( f"Delay completed, proceeding with execution" );
    else:
        logger.info( "Interactive execution detected - no delay applied" );

def main():
    parser = argparse.ArgumentParser(
        description='KC New Restaurants Monitor - Download and track Kansas City food business licenses'
    );
    parser.add_argument(
        '--ephemeral', '-e',
        action='store_true',
        help='Run in ephemeral mode without MongoDB (for testing/debugging)'
    );
    parser.add_argument(
        '--flush', '-f',
        action='store_true',
        help='Flush (truncate) the database collection before processing to start fresh'
    );
    parser.add_argument(
        '--nodelay',
        action='store_true',
        help='Skip the random delay even when running under cron (use with caution)'
    );
    parser.add_argument(
        '--dry-run', '--dryrun', '-d',
        action='store_true',
        dest='dry_run',
        help='Run in dry-run mode - no database modifications will be performed (safe testing mode)'
    );
    parser.add_argument(
        '--no-enrichment',
        action='store_true',
        help='Disable Google Places enrichment (faster processing, basic data only)'
    );
    
    args = parser.parse_args();
    
    # Display dry-run banner if enabled
    if args.dry_run:
        print( "\n" + "="*70 );
        print( "*** DRY-RUN MODE: NO DATA WILL BE MODIFIED ***" );
        print( "  - All database operations will be simulated only" );
        print( "  - No actual INSERT, UPDATE, or DELETE operations will occur" );
        print( "  - This is safe for testing and validation" );
        print( "="*70 + "\n" );
        logger.info( "DRY-RUN MODE ENABLED - No database modifications will be performed" );
    
    apply_random_delay( skip_delay=args.nodelay );

    CONFIG = {
        'mongodb_uri': os.getenv( "mongodb_uri", "" ),
        'database_name': "kansas_city",
        'collection_name': "food_businesses",
        'smtp_server': "smtp.gmail.com",
        'smtp_port': 587,
        'sender_email': os.getenv( "gmail_sender_email", "" ),  # Your Gmail address
        'sender_password': os.getenv( "gmail_sender_password", "" ),  # Your Gmail App Password
        'recipient_email': os.getenv( "gmail_recipient_email", "" ),      # Where to send alerts
        'email_subject': f"KC Food Business Alert - {datetime.now().strftime('%Y-%m-%d')}"
    };

    runner = KCRestaurant( CONFIG[ 'mongodb_uri' ], CONFIG[ 'database_name' ], CONFIG[ 'collection_name' ], dry_run=args.dry_run, enable_enrichment=not args.no_enrichment );
    
    #  ephemeral mode
    if args.ephemeral:
        print( "\nEPHEMERAL MODE: Running without MongoDB persistence (testing/debugging mode)" );
        print( "   - No database connection will be established" );
        print( "   - All businesses will be treated as 'new' for this run" );
        print( "   - No data will be persisted between runs\n" );
    elif args.dry_run:
        print( "\nDRY-RUN MODE: Database operations will be simulated only" );
        print( "   - MongoDB connection will be established but no writes will occur" );
        print( "   - All INSERT, UPDATE, DELETE operations will be logged but skipped" );
        print( "   - Safe for testing against production data\n" );
        
        # In dry-run mode, we still need to connect to MongoDB for duplicate detection
        if MONGODB_AVAILABLE:
            if not runner.setup_mongodb():
                print( "\nMongoDB setup failed. Running in ephemeral mode." );
        else:
            print( "\nPyMongo not available. Running in ephemeral mode." );

    elif MONGODB_AVAILABLE:
        if not runner.setup_mongodb():
            print( "\nMongoDB setup failed. Running in ephemeral mode." );
        else:

            if args.flush:
                print( "\nFLUSH MODE: Clearing all existing data from database..." );
                if runner.flush_database():
                    print( "Database flushed successfully. All records will appear as new.\n" );
                else:
                    print( "Failed to flush database. Exiting." );
                    return;
    else:
        print( "\nPyMongo not available. Running in ephemeral mode." );
    
    runner.run();

    if all( [ CONFIG[ 'sender_email' ], CONFIG[ 'sender_password' ], CONFIG[ 'recipient_email' ] ] ):
        print( f"\nSending email alert..." );
        success = runner.send_email_alert(
            smtp_server=CONFIG[ 'smtp_server' ],
            smtp_port=CONFIG[ 'smtp_port' ],
            sender_email=CONFIG[ 'sender_email' ],
            sender_password=CONFIG[ 'sender_password' ],
            recipient_email=CONFIG[ 'recipient_email' ],
            subject=CONFIG[ 'email_subject' ]
        );
        if success:
            print( "Email alert sent successfully" );
        else:
            print( "Email alert failed" );
    else:
        print( f"\nEmail not configured:" );
        print( "To enable email alerts, update the CONFIG section with:" );
        print( "* sender_email: Your Gmail address" );
        print( "* sender_password: Your Gmail App Password" );  
        print( "* recipient_email: Where to send alerts" );

if __name__ == "__main__":
    main();

