#!/usr/bin/env python3
"""
Test script for health inspection client
"""

import sys;
import os;
import logging;

# Add parent directory to path for imports
sys.path.insert( 0, os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) );

from services.health_inspection_client import HealthInspectionClient;

# Configure logging
logging.basicConfig( level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s' );
logger = logging.getLogger( __name__ );

def test_health_inspection():
    """Test health inspection client with known restaurants."""
    
    logger.info( "Testing health inspection client..." );
    
    try:
        # Initialize client
        client = HealthInspectionClient( rate_limit_delay=2.0 );  # Slow for testing
        
        # Test restaurants (known Kansas City establishments)
        test_restaurants = [
            ( "Joe's Kansas City Bar-B-Que", "3002 W 47th Ave, Kansas City, KS" ),
            ( "Q39", "1000 W 39th St, Kansas City, MO" ),
            ( "Grinder's Pizza", "417 E 18th St, Kansas City, MO" ),
        ];
        
        for name, address in test_restaurants:
            logger.info( f"\n{'='*60}" );
            logger.info( f"Testing: {name}" );
            logger.info( f"Address: {address}" );
            logger.info( f"{'='*60}" );
            
            grade = client.get_health_grade( name, address );
            
            if grade:
                print( f"\n✅ Results for {name}:" );
                print( f"   Health Grade: {grade.letter_grade}" );
                print( f"   Explanation: {grade.grade_explanation}" );
                print( f"   Total Inspections: {grade.total_inspections}" );
                print( f"   Last Inspection: {grade.last_inspection_date}" );
                print( f"   Avg Critical Violations: {grade.average_critical:.1f}" );
                print( f"   Avg Non-Critical Violations: {grade.average_noncritical:.1f}" );
            else:
                print( f"\n❌ No health inspection data found for {name}" );
            
            # Pause between requests
            import time;
            time.sleep( 2 );
        
        logger.info( "\n✅ Health inspection client test completed" );
        
    except Exception as e:
        logger.error( f"❌ Test failed: {e}" );
        import traceback;
        traceback.print_exc();

if __name__ == "__main__":
    test_health_inspection();
