#!/bin/bash

# MongoDB Restaurant Query Helper
# Usage: ./query_restaurants.sh [command]

MONGO_URI="$mongodb_uri"
DB="kansas_city"
COLLECTION="food_businesses"

if [ -z "$1" ]; then
    echo "MongoDB Restaurant Query Helper"
    echo "================================"
    echo "Usage: $0 [command]"
    echo ""
    echo "Available commands:"
    echo "  count          - Count all restaurants"
    echo "  types          - Group by business types" 
    echo "  recent [days]  - Show recent additions (default: 7 days)"
    echo "  search [term]  - Search business names"
    echo "  sample         - Show sample document"
    echo "  bakeries       - Show all bakeries"
    echo "  mobile         - Show mobile food services"
    echo "  custom         - Open interactive MongoDB shell"
    echo ""
    echo "Examples:"
    echo "  $0 count"
    echo "  $0 recent 30"
    echo "  $0 search pizza"
    exit 1
fi

case $1 in
    "count")
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Total restaurants in database:', db.$COLLECTION.countDocuments());
        "
        ;;
    
    "types") 
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Business Types (COUNT - TYPE):');
        print('===============================');
        db.$COLLECTION.aggregate([
          { \$group: { _id: '\$business_type', count: { \$sum: 1 } } },
          { \$sort: { count: -1 } }
        ]).forEach(doc => print(doc.count.toString().padStart(3) + ' - ' + doc._id));
        "
        ;;
        
    "recent")
        DAYS=${2:-7}
        DATE=$(date -d "$DAYS days ago" +%Y-%m-%d)
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Recent additions (last $DAYS days since $DATE):');
        print('================================================');
        db.$COLLECTION.find(
          { insert_date: { \$gte: '$DATE' } }
        ).sort({ insert_date: -1 }).forEach(doc => 
          print(doc.insert_date + ' | ' + doc.business_name + ' | ' + doc.address)
        );
        "
        ;;
        
    "search")
        if [ -z "$2" ]; then
            echo "Usage: $0 search [term]"
            exit 1
        fi
        TERM="$2"
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Search results for: $TERM');
        print('========================');
        db.$COLLECTION.find(
          { business_name: { \$regex: '$TERM', \$options: 'i' } },
          { business_name: 1, address: 1, business_type: 1 }
        ).forEach(doc => 
          print(doc.business_name + ' | ' + doc.address + ' | ' + doc.business_type)
        );
        "
        ;;
        
    "sample")
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Sample document:');
        print('===============');
        printjson(db.$COLLECTION.findOne());
        "
        ;;
        
    "bakeries")
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('All Bakeries:');
        print('============');
        db.$COLLECTION.find(
          { business_type: 'Retail Bakeries' },
          { business_name: 1, address: 1 }
        ).forEach(doc => 
          print(doc.business_name + ' | ' + doc.address)
        );
        "
        ;;
        
    "mobile")
        mongosh "$MONGO_URI" --quiet --eval "
        db = db.getSiblingDB('$DB');
        print('Mobile Food Services:');
        print('====================');
        db.$COLLECTION.find(
          { business_type: 'Mobile Food Services' },
          { business_name: 1, address: 1 }
        ).forEach(doc => 
          print(doc.business_name + ' | ' + doc.address)
        );
        "
        ;;
        
    "custom")
        echo "Opening interactive MongoDB shell..."
        echo "Connected to database: $DB"
        echo "Collection: $COLLECTION"
        echo "Example queries:"
        echo "  db.$COLLECTION.find().limit(5)"
        echo "  db.$COLLECTION.countDocuments()"
        echo "  exit"
        mongosh "$MONGO_URI" --eval "use $DB"
        ;;
        
    *)
        echo "Unknown command: $1"
        echo "Run '$0' without arguments to see available commands."
        exit 1
        ;;
esac
