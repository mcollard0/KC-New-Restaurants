#!/usr/bin/env python3
"""
Dual Database Manager
Supports both MongoDB (primary) and SQLite (local storage) for KC New Restaurants data
"""

import os
import sqlite3
import json
import logging
import ssl
import certifi
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages both MongoDB (primary) and SQLite (local backup) databases"""
    
    def __init__(self, mongodb_uri: Optional[str] = None, sqlite_path: Optional[str] = None):
        """
        Initialize dual database manager
        
        Args:
            mongodb_uri: MongoDB connection string (defaults to env var)
            sqlite_path: SQLite database file path (defaults to local file)
        """
        self.mongodb_uri = mongodb_uri or os.getenv('MONGODB_URI') or os.getenv('mongodb_uri')
        self.sqlite_path = sqlite_path or os.path.join(os.getcwd(), 'data', 'kc_restaurants.db')
        
        # Database connections
        self.mongo_client = None
        self.mongo_collection = None
        self.sqlite_conn = None
        
        # Connection status
        self.mongodb_available = False
        self.sqlite_available = False
        
        # Initialize databases
        self._initialize_mongodb()
        self._initialize_sqlite()
        
        logger.info(f"Database Manager initialized - MongoDB: {'✅' if self.mongodb_available else '❌'}, SQLite: {'✅' if self.sqlite_available else '❌'}")
    
    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        if not self.mongodb_uri:
            logger.warning("No MongoDB URI provided, MongoDB will be disabled")
            return
            
        try:
            # Configure SSL/TLS for MongoDB Atlas connections
            try:
                # First attempt: Use certifi CA bundle with TLS
                self.mongo_client = MongoClient(
                    self.mongodb_uri,
                    tls=True,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=10000,
                    tlsAllowInvalidCertificates=False
                )
            except Exception as ssl_error:
                logger.warning(f"Standard TLS connection failed, trying fallback with relaxed settings: {ssl_error}")
                # Second attempt: Allow invalid certificates (fallback for systems with old SSL)
                self.mongo_client = MongoClient(
                    self.mongodb_uri,
                    tls=True,
                    serverSelectionTimeoutMS=10000,
                    tlsAllowInvalidCertificates=True
                )
            
            # Test connection
            self.mongo_client.server_info()
            
            # Setup database and collection
            db = self.mongo_client['kansas_city']
            self.mongo_collection = db['food_businesses']
            
            self.mongodb_available = True
            logger.info("MongoDB connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.mongodb_available = False
    
    def _initialize_sqlite(self):
        """Initialize SQLite database and create tables"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            
            self.sqlite_conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
            self.sqlite_conn.row_factory = sqlite3.Row  # Enable dict-like access
            
            # Create tables
            self._create_sqlite_tables()
            
            self.sqlite_available = True
            logger.info(f"SQLite database initialized: {self.sqlite_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")
            self.sqlite_available = False
    
    def _create_sqlite_tables(self):
        """Create SQLite tables for restaurant data"""
        cursor = self.sqlite_conn.cursor()
        
        # Main restaurants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS food_businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                dba_name TEXT,
                address TEXT,
                business_type TEXT,
                valid_license_for TEXT,
                insert_date TEXT,
                deleted BOOLEAN DEFAULT 0,
                
                -- Google Places data
                google_place_id TEXT,
                google_rating REAL,
                google_user_ratings_total INTEGER,
                google_formatted_address TEXT,
                google_name TEXT,
                cuisine_type TEXT,
                price_level INTEGER,
                latitude REAL,
                longitude REAL,
                
                -- Amenities (JSON stored as TEXT)
                outdoor_seating BOOLEAN,
                takeout_available BOOLEAN,
                delivery_available BOOLEAN,
                reservations_accepted BOOLEAN,
                wheelchair_accessible BOOLEAN,
                good_for_children BOOLEAN,
                serves_alcohol BOOLEAN,
                parking_available BOOLEAN,
                business_hours TEXT,  -- JSON
                
                -- Review analysis
                sentiment_avg REAL,
                sentiment_distribution TEXT,  -- JSON
                review_keywords TEXT,  -- JSON array
                sentiment_summary TEXT,
                review_summary TEXT,
                
                -- AI predictions
                ai_predicted_rating REAL,
                ai_predicted_grade TEXT,
                ai_prediction_confidence TEXT,
                ai_confidence_percentage INTEGER,
                ai_confidence_level TEXT,
                ai_similar_restaurants_count INTEGER,
                ai_prediction_explanation TEXT,
                
                -- Health inspection data
                health_inspection_grade TEXT,
                health_avg_critical REAL,
                health_avg_noncritical REAL,
                health_total_inspections INTEGER,
                health_last_inspection_date TEXT,
                health_grade_explanation TEXT,
                
                -- Metadata
                enriched_date TEXT,
                api_fields_retrieved TEXT,  -- JSON array
                last_updated TEXT,
                
                UNIQUE(business_name, address)
            )
        ''')
        
        # Create health_inspections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER,  -- Link to food_businesses.id
                establishment_name TEXT,
                address TEXT,
                inspection_date TEXT,
                inspection_type TEXT,
                critical_violations INTEGER,
                non_critical_violations INTEGER,
                violations_desc TEXT,
                source_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(restaurant_id) REFERENCES food_businesses(id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_business_name 
            ON food_businesses(business_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_location 
            ON food_businesses(latitude, longitude)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cuisine_type 
            ON food_businesses(cuisine_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_google_place_id 
            ON food_businesses(google_place_id)
        ''')
        
        self.sqlite_conn.commit()
        logger.debug("SQLite tables created successfully")
    
    def insert_document(self, document: Dict[str, Any]) -> bool:
        """
        Insert document into both databases
        
        Args:
            document: Restaurant document to insert
            
        Returns:
            True if inserted successfully into at least one database
        """
        success_mongo = False
        success_sqlite = False
        
        # Insert into MongoDB (primary)
        if self.mongodb_available:
            try:
                result = self.mongo_collection.insert_one(document.copy())
                success_mongo = bool(result.inserted_id)
                if success_mongo:
                    logger.debug(f"Document inserted into MongoDB: {document.get('business_name')}")
            except Exception as e:
                logger.error(f"Failed to insert into MongoDB: {e}")
        
        # Insert into SQLite (backup)
        if self.sqlite_available:
            try:
                success_sqlite = self._insert_sqlite_document(document)
                if success_sqlite:
                    logger.debug(f"Document inserted into SQLite: {document.get('business_name')}")
            except Exception as e:
                logger.error(f"Failed to insert into SQLite: {e}")
        
        return success_mongo or success_sqlite
    
    def _insert_sqlite_document(self, document: Dict[str, Any]) -> bool:
        """Insert document into SQLite database"""
        cursor = self.sqlite_conn.cursor()
        
        # Convert complex fields to JSON
        doc = document.copy()
        json_fields = ['business_hours', 'sentiment_distribution', 'review_keywords', 'api_fields_retrieved']
        
        for field in json_fields:
            if field in doc and doc[field] is not None:
                doc[field] = json.dumps(doc[field])
        
        # Prepare column names and values
        columns = []
        values = []
        placeholders = []
        
        # Map document fields to SQLite columns
        field_mapping = {
            '_id': None,  # Skip MongoDB ObjectId
            'business_name': 'business_name',
            'dba_name': 'dba_name',
            'address': 'address',
            'business_type': 'business_type',
            'valid_license_for': 'valid_license_for',
            'insert_date': 'insert_date',
            'deleted': 'deleted',
            'google_place_id': 'google_place_id',
            'google_rating': 'google_rating',
            'google_user_ratings_total': 'google_user_ratings_total',
            'google_formatted_address': 'google_formatted_address',
            'google_name': 'google_name',
            'cuisine_type': 'cuisine_type',
            'price_level': 'price_level',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'outdoor_seating': 'outdoor_seating',
            'takeout_available': 'takeout_available',
            'delivery_available': 'delivery_available',
            'reservations_accepted': 'reservations_accepted',
            'wheelchair_accessible': 'wheelchair_accessible',
            'good_for_children': 'good_for_children',
            'serves_alcohol': 'serves_alcohol',
            'parking_available': 'parking_available',
            'business_hours': 'business_hours',
            'sentiment_avg': 'sentiment_avg',
            'sentiment_distribution': 'sentiment_distribution',
            'review_keywords': 'review_keywords',
            'sentiment_summary': 'sentiment_summary',
            'review_summary': 'review_summary',
            'ai_predicted_rating': 'ai_predicted_rating',
            'ai_predicted_grade': 'ai_predicted_grade',
            'ai_prediction_confidence': 'ai_prediction_confidence',
            'ai_confidence_percentage': 'ai_confidence_percentage',
            'ai_confidence_level': 'ai_confidence_level',
            'ai_similar_restaurants_count': 'ai_similar_restaurants_count',
            'ai_prediction_explanation': 'ai_prediction_explanation',
            'enriched_date': 'enriched_date',
            'api_fields_retrieved': 'api_fields_retrieved',
            'last_updated': 'last_updated'
        }
        
        for doc_field, db_field in field_mapping.items():
            if db_field and doc_field in doc:
                columns.append(db_field)
                values.append(doc[doc_field])
                placeholders.append('?')
        
        if not columns:
            return False
        
        # Build and execute INSERT statement
        sql = f"INSERT OR REPLACE INTO food_businesses ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        cursor.execute(sql, values)
        self.sqlite_conn.commit()
        
        return cursor.rowcount > 0
    
    def find(self, query: Dict[str, Any] = None, limit: int = 0):
        """
        MongoDB-compatible find method (returns iterable)
        Used by AI predictor and other components expecting MongoDB interface
        """
        return self.find_documents(query, limit)
    
    def find_documents(self, query: Dict[str, Any] = None, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Find documents from primary database (MongoDB preferred, SQLite fallback)
        
        Args:
            query: Query criteria (MongoDB style)
            limit: Maximum number of documents to return
            
        Returns:
            List of matching documents
        """
        # Try MongoDB first
        if self.mongodb_available:
            try:
                cursor = self.mongo_collection.find(query or {})
                if limit > 0:
                    cursor = cursor.limit(limit)
                
                documents = list(cursor)
                logger.debug(f"Found {len(documents)} documents in MongoDB")
                return documents
                
            except Exception as e:
                logger.error(f"Failed to query MongoDB: {e}")
        
        # Fallback to SQLite
        if self.sqlite_available:
            try:
                return self._find_sqlite_documents(query, limit)
            except Exception as e:
                logger.error(f"Failed to query SQLite: {e}")
        
        return []
    
    def _find_sqlite_documents(self, query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Find documents in SQLite database with MongoDB-style operators"""
        cursor = self.sqlite_conn.cursor()
        
        # Build WHERE clause from query (with MongoDB operator support)
        where_parts = []
        params = []
        
        if query:
            for field, value in query.items():
                if field == 'deleted' and isinstance(value, bool):
                    where_parts.append(f"{field} = ?")
                    params.append(1 if value else 0)
                elif isinstance(value, dict):
                    # Handle MongoDB operators
                    for operator, op_value in value.items():
                        if operator == '$exists':
                            if op_value:
                                where_parts.append(f"{field} IS NOT NULL")
                            else:
                                where_parts.append(f"{field} IS NULL")
                        elif operator == '$ne':
                            if op_value is None:
                                where_parts.append(f"{field} IS NOT NULL")
                            else:
                                where_parts.append(f"({field} IS NULL OR {field} != ?)")
                                params.append(op_value)
                        elif operator == '$gte':
                            where_parts.append(f"{field} >= ?")
                            params.append(op_value)
                        elif operator == '$lte':
                            where_parts.append(f"{field} <= ?")
                            params.append(op_value)
                        elif operator == '$gt':
                            where_parts.append(f"{field} > ?")
                            params.append(op_value)
                        elif operator == '$lt':
                            where_parts.append(f"{field} < ?")
                            params.append(op_value)
                elif isinstance(value, (str, int, float)):
                    where_parts.append(f"{field} = ?")
                    params.append(value)
        
        sql = "SELECT * FROM food_businesses"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        
        if limit > 0:
            sql += f" LIMIT {limit}"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries and parse JSON fields
        documents = []
        json_fields = ['business_hours', 'sentiment_distribution', 'review_keywords', 'api_fields_retrieved']
        
        for row in rows:
            doc = dict(row)
            
            # Parse JSON fields
            for field in json_fields:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            documents.append(doc)
        
        logger.debug(f"Found {len(documents)} documents in SQLite")
        return documents
    
    def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents in primary database"""
        # Try MongoDB first
        if self.mongodb_available:
            try:
                count = self.mongo_collection.count_documents(query or {})
                logger.debug(f"MongoDB document count: {count}")
                return count
            except Exception as e:
                logger.error(f"Failed to count MongoDB documents: {e}")
        
        # Fallback to SQLite
        if self.sqlite_available:
            try:
                cursor = self.sqlite_conn.cursor()
                
                where_parts = []
                params = []
                
                if query:
                    for field, value in query.items():
                        if field == 'deleted' and isinstance(value, bool):
                            where_parts.append(f"{field} = ?")
                            params.append(1 if value else 0)
                        elif isinstance(value, (str, int, float)):
                            where_parts.append(f"{field} = ?")
                            params.append(value)
                
                sql = "SELECT COUNT(*) FROM food_businesses"
                if where_parts:
                    sql += " WHERE " + " AND ".join(where_parts)
                
                cursor.execute(sql, params)
                count = cursor.fetchone()[0]
                logger.debug(f"SQLite document count: {count}")
                return count
                
            except Exception as e:
                logger.error(f"Failed to count SQLite documents: {e}")
        
        return 0
    
    def delete_many(self, query: Dict[str, Any] = None):
        """Delete documents from both databases"""
        
        # Create a result object compatible with pymongo
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
        
        deleted_count = 0
        
        # Delete from MongoDB
        if self.mongodb_available:
            try:
                result = self.mongo_collection.delete_many(query or {})
                deleted_count = result.deleted_count
                logger.info(f"Deleted {deleted_count} documents from MongoDB")
            except Exception as e:
                logger.error(f"Failed to delete from MongoDB: {e}")
        
        # Delete from SQLite
        if self.sqlite_available:
            try:
                cursor = self.sqlite_conn.cursor()
                
                where_parts = []
                params = []
                
                if query:
                    for field, value in query.items():
                        if field == 'deleted' and isinstance(value, bool):
                            where_parts.append(f"{field} = ?")
                            params.append(1 if value else 0)
                        elif isinstance(value, (str, int, float)):
                            where_parts.append(f"{field} = ?")
                            params.append(value)
                
                sql = "DELETE FROM food_businesses"
                if where_parts:
                    sql += " WHERE " + " AND ".join(where_parts)
                else:
                    sql += " WHERE 1=1"  # Delete all if no query
                
                cursor.execute(sql, params)
                self.sqlite_conn.commit()
                
                sqlite_deleted = cursor.rowcount
                if sqlite_deleted > 0:
                    deleted_count = sqlite_deleted
                logger.info(f"Deleted {sqlite_deleted} documents from SQLite")
                
            except Exception as e:
                logger.error(f"Failed to delete from SQLite: {e}")
        
        return DeleteResult(deleted_count)
    
    def get_collection(self) -> Optional[Union[Collection, 'DatabaseManager']]:
        """
        Get the primary collection for compatibility with existing code
        Returns MongoDB collection if available, otherwise returns self for SQLite operations
        """
        if self.mongodb_available:
            return self.mongo_collection
        elif self.sqlite_available:
            return self  # Return self to handle SQLite operations
        else:
            return None
    
    def close(self):
        """Close all database connections"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.debug("MongoDB connection closed")
        
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.debug("SQLite connection closed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of both databases"""
        status = {
            'mongodb': {
                'available': self.mongodb_available,
                'uri': self.mongodb_uri[:50] + '...' if self.mongodb_uri and len(self.mongodb_uri) > 50 else self.mongodb_uri
            },
            'sqlite': {
                'available': self.sqlite_available,
                'path': self.sqlite_path
            }
        }
        
        # Get document counts
        if self.mongodb_available or self.sqlite_available:
            status['document_count'] = self.count_documents({'deleted': False})
        
        return status


# Compatibility wrapper for existing code
class DatabaseManagerWrapper:
    """Wrapper to make DatabaseManager compatible with existing MongoDB collection usage"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def insert_one(self, document: Dict[str, Any]):
        """MongoDB-style insert_one compatibility"""
        class InsertResult:
            def __init__(self, success: bool):
                self.inserted_id = "sqlite_id" if success else None
        
        success = self.db_manager.insert_document(document)
        return InsertResult(success)
    
    def find(self, query: Dict[str, Any] = None, limit: int = 0):
        """MongoDB-style find compatibility"""
        documents = self.db_manager.find_documents(query, limit)
        return documents  # Return list directly instead of cursor
    
    def find_one(self, query: Dict[str, Any] = None):
        """MongoDB-style find_one compatibility"""
        documents = self.db_manager.find_documents(query, limit=1)
        return documents[0] if documents else None
    
    def count_documents(self, query: Dict[str, Any] = None):
        """MongoDB-style count_documents compatibility"""
        return self.db_manager.count_documents(query)
    
    def delete_many(self, query: Dict[str, Any] = None):
        """MongoDB-style delete_many compatibility"""
        class DeleteResult:
            def __init__(self, deleted_count: int):
                self.deleted_count = deleted_count
        
        deleted_count = self.db_manager.delete_many(query)
        return DeleteResult(deleted_count)


if __name__ == "__main__":
    # Test the database manager
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Test basic operations
    test_doc = {
        'business_name': 'Test Restaurant',
        'address': '123 Test St',
        'business_type': 'Restaurant',
        'insert_date': datetime.now().isoformat(),
        'deleted': False
    }
    
    # Test insert
    success = db_manager.insert_document(test_doc)
    print(f"Insert test: {'✅' if success else '❌'}")
    
    # Test find
    documents = db_manager.find_documents({'business_name': 'Test Restaurant'})
    print(f"Find test: {'✅' if documents else '❌'} (found {len(documents)} documents)")
    
    # Test count
    count = db_manager.count_documents()
    print(f"Count test: {count} documents")
    
    # Get status
    status = db_manager.get_status()
    print(f"Status: {status}")
    
    # Cleanup
    db_manager.delete_many({'business_name': 'Test Restaurant'})
    db_manager.close()
