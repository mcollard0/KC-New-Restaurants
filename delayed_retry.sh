#!/bin/bash

echo "🕐 Starting delayed retry script at $(date)"
echo "⏰ Waiting 3600 seconds (1 hour) for Google Cloud changes to propagate..."
echo "💤 Sleep started at: $(date)"

# Wait for 1 hour
sleep 3600

echo "⏰ Sleep complete at: $(date)"
echo "🗄️  Truncating MongoDB collection..."

# Truncate the MongoDB collection
python3 -c "
import os
from pymongo import MongoClient

# MongoDB connection
mongo_uri = os.getenv('MONGODB_URI') or os.getenv('mongodb_uri')
client = MongoClient(mongo_uri)
db = client['kansas_city']
collection = db['food_businesses']

# Count and delete all documents
initial_count = collection.count_documents({})
print(f'Found {initial_count} documents in collection')

if initial_count > 0:
    result = collection.delete_many({})
    print(f'✅ Successfully purged {result.deleted_count} documents')
else:
    print('Collection already empty')

# Verify cleanup
final_count = collection.count_documents({})
print(f'Collection now contains {final_count} documents')
print('🚀 Ready for real Google Places API data!')

client.close()
"

echo "🚀 Starting KC New Restaurants with real Google Places API data..."
echo "▶️  Run started at: $(date)"

# Run the main program
timeout 300 python3 "KC New Restaurants.py"

echo "✅ Run completed at: $(date)"
