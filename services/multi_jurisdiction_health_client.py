#!/usr/bin/env python3
"""
Multi-Jurisdiction Health Inspection Client
Supports Kansas City MO, Kansas City KS, and surrounding cities
Prioritizes jurisdictions based on restaurant density
"""

import requests;
import re;
import logging;
import time;
from typing import List, Dict, Optional, Tuple, Set;
from dataclasses import dataclass;
from datetime import datetime;
from bs4 import BeautifulSoup;
from collections import Counter;

logger = logging.getLogger( __name__ );

@dataclass
class InspectionRecord:
    """Single inspection record."""
    date: str;
    critical_violations: int;
    noncritical_violations: int;
    jurisdiction: str;
    inspection_type: Optional[str] = None;
    score: Optional[int] = None;

@dataclass
class HealthGrade:
    """Health inspection grade result."""
    letter_grade: str;
    average_critical: float;
    average_noncritical: float;
    total_inspections: int;
    inspections: List[InspectionRecord];
    jurisdiction: str;
    last_inspection_date: Optional[str] = None;
    grade_explanation: Optional[str] = None;

@dataclass
class JurisdictionConfig:
    """Configuration for a health inspection jurisdiction."""
    name: str;
    base_url: str;
    search_url: str;
    city_patterns: List[str];  # City name patterns to match
    priority: int = 0;  # Higher = search first (calculated from restaurant density)

class MultiJurisdictionHealthClient:
    """Client for fetching health inspection data from multiple jurisdictions."""
    
    def __init__( self, rate_limit_delay: float = 1.0, mongodb_collection=None ):
        """
        Initialize multi-jurisdiction health inspection client.
        
        Args:
            rate_limit_delay: Delay between requests in seconds (default: 1.0)
            mongodb_collection: MongoDB collection for analyzing restaurant density
        """
        self.rate_limit_delay = rate_limit_delay;
        self.session = requests.Session();
        self.session.headers.update( {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        } );
        self.last_request_time = 0;
        self.mongodb_collection = mongodb_collection;
        
        # Define jurisdictions
        self.jurisdictions = [
            JurisdictionConfig(
                name="Kansas City MO",
                base_url="https://www.inspectionsonline.us/mo/usakansascity/inspect.nsf",
                search_url="https://www.inspectionsonline.us/mo/usakansascity/inspect.nsf/Search?OpenForm",
                city_patterns=["kansas city mo", "kcmo", "kc mo"]
            ),
            JurisdictionConfig(
                name="Kansas City KS (Wyandotte County)",
                base_url="https://www.inspectionsonline.us/ks/wyandotte/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/wyandotte/inspect.nsf/Search?OpenForm",
                city_patterns=["kansas city ks", "kck", "kc ks", "wyandotte"]
            ),
            JurisdictionConfig(
                name="Overland Park KS",
                base_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf/Search?OpenForm",
                city_patterns=["overland park", "op ks"]
            ),
            JurisdictionConfig(
                name="Olathe KS",
                base_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf/Search?OpenForm",
                city_patterns=["olathe"]
            ),
            JurisdictionConfig(
                name="Lenexa KS",
                base_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf/Search?OpenForm",
                city_patterns=["lenexa"]
            ),
            JurisdictionConfig(
                name="Shawnee KS",
                base_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf/Search?OpenForm",
                city_patterns=["shawnee"]
            ),
            JurisdictionConfig(
                name="Leawood KS",
                base_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf",
                search_url="https://www.inspectionsonline.us/ks/joco/inspect.nsf/Search?OpenForm",
                city_patterns=["leawood"]
            ),
            JurisdictionConfig(
                name="Independence MO",
                base_url="https://www.inspectionsonline.us/mo/independence/inspect.nsf",
                search_url="https://www.inspectionsonline.us/mo/independence/inspect.nsf/Search?OpenForm",
                city_patterns=["independence"]
            ),
            JurisdictionConfig(
                name="Lee's Summit MO",
                base_url="https://www.inspectionsonline.us/mo/leessummit/inspect.nsf",
                search_url="https://www.inspectionsonline.us/mo/leessummit/inspect.nsf/Search?OpenForm",
                city_patterns=["lee's summit", "lees summit", "ls mo"]
            ),
            JurisdictionConfig(
                name="Blue Springs MO",
                base_url="https://www.inspectionsonline.us/mo/bluesprings/inspect.nsf",
                search_url="https://www.inspectionsonline.us/mo/bluesprings/inspect.nsf/Search?OpenForm",
                city_patterns=["blue springs"]
            )
        ];
        
        # Calculate jurisdiction priorities based on restaurant density
        self._calculate_jurisdiction_priorities();
        
        logger.info( f"Multi-jurisdiction health inspection client initialized with {len( self.jurisdictions )} jurisdictions" );
        self._log_jurisdiction_priorities();
    
    def _calculate_jurisdiction_priorities( self ):
        """Calculate priority for each jurisdiction based on restaurant density in database."""
        if not self.mongodb_collection:
            logger.warning( "No database connection - using default jurisdiction priorities" );
            return;
        
        try:
            # Count restaurants by city from addresses
            pipeline = [
                { "$match": { "address": { "$exists": True } } },
                { "$project": { "address": 1 } }
            ];
            
            restaurants = list( self.mongodb_collection.aggregate( pipeline, allowDiskUse=True ) );
            
            # Extract cities from addresses and count
            city_counts = Counter();
            
            for restaurant in restaurants:
                address = restaurant.get( "address", "" ).lower();
                
                # Try to match jurisdiction patterns
                for jurisdiction in self.jurisdictions:
                    for pattern in jurisdiction.city_patterns:
                        if pattern in address:
                            city_counts[jurisdiction.name] += 1;
                            break;
            
            # Assign priorities based on counts
            for jurisdiction in self.jurisdictions:
                count = city_counts.get( jurisdiction.name, 0 );
                jurisdiction.priority = count;
            
            # Sort jurisdictions by priority (descending)
            self.jurisdictions.sort( key=lambda x: x.priority, reverse=True );
            
            logger.info( "Calculated jurisdiction priorities based on restaurant density" );
            
        except Exception as e:
            logger.warning( f"Could not calculate jurisdiction priorities: {e}" );
    
    def _log_jurisdiction_priorities( self ):
        """Log jurisdiction priorities for debugging."""
        logger.info( "Jurisdiction priorities (restaurants per jurisdiction):" );
        for jurisdiction in self.jurisdictions:
            logger.info( f"  {jurisdiction.name}: {jurisdiction.priority} restaurants" );
    
    def _rate_limit( self ):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time;
        if elapsed < self.rate_limit_delay:
            time.sleep( self.rate_limit_delay - elapsed );
        self.last_request_time = time.time();
    
    def _detect_jurisdiction( self, address: str ) -> Optional[JurisdictionConfig]:
        """
        Detect which jurisdiction a restaurant belongs to based on address.
        
        Args:
            address: Restaurant address
            
        Returns:
            JurisdictionConfig or None
        """
        address_lower = address.lower();
        
        for jurisdiction in self.jurisdictions:
            for pattern in jurisdiction.city_patterns:
                if pattern in address_lower:
                    return jurisdiction;
        
        # Default to Kansas City MO if no match
        return self.jurisdictions[0];
    
    def _search_facility( self, facility_name: str, street_name: Optional[str], jurisdiction: JurisdictionConfig ) -> Optional[str]:
        """
        Search for a facility in a specific jurisdiction.
        
        Args:
            facility_name: Name of the restaurant
            street_name: Optional street name to narrow search
            jurisdiction: Jurisdiction to search in
            
        Returns:
            URL to inspection results or None if not found
        """
        self._rate_limit();
        
        try:
            # Prepare search parameters
            search_params = {
                'SearchView': '',
                'Query': f'[Facility_Name] contains "{facility_name}"'
            };
            
            if street_name:
                # Extract street name without number
                street_cleaned = re.sub( r'^\d+\s+', '', street_name ).strip();
                search_params['Query'] += f' AND [Street_Name] contains "{street_cleaned}"';
            
            logger.debug( f"Searching in {jurisdiction.name}: {facility_name}" );
            
            response = self.session.post( jurisdiction.search_url, data=search_params, timeout=10 );
            response.raise_for_status();
            
            soup = BeautifulSoup( response.text, 'html.parser' );
            
            # Look for results link
            results_links = soup.find_all( 'a', href=re.compile( r'Facility\?OpenDocument' ) );
            
            if results_links:
                first_link = results_links[0];
                facility_url = first_link.get( 'href' );
                
                # Make URL absolute
                if not facility_url.startswith( 'http' ):
                    facility_url = jurisdiction.base_url + '/' + facility_url.lstrip( '/' );
                
                logger.debug( f"Found facility URL in {jurisdiction.name}: {facility_url}" );
                return facility_url;
            
            return None;
            
        except Exception as e:
            logger.debug( f"Error searching {jurisdiction.name} for {facility_name}: {e}" );
            return None;
    
    def _parse_inspections( self, html_content: str, jurisdiction_name: str ) -> List[InspectionRecord]:
        """Parse inspection records from facility page HTML."""
        inspections = [];
        
        try:
            soup = BeautifulSoup( html_content, 'html.parser' );
            
            # Find inspection links/rows
            inspection_links = soup.find_all( 'a', href=re.compile( r'Inspection\?OpenDocument' ) );
            
            for link in inspection_links:
                try:
                    parent_row = link.find_parent( 'tr' );
                    if not parent_row:
                        continue;
                    
                    cells = parent_row.find_all( 'td' );
                    
                    if len( cells ) < 3:
                        continue;
                    
                    date_text = cells[0].get_text( strip=True ) if len( cells ) > 0 else "";
                    text_content = parent_row.get_text();
                    
                    # Extract violation counts
                    critical_match = re.search( r'(\d+)\s*critical', text_content, re.IGNORECASE );
                    noncritical_match = re.search( r'(\d+)\s*non-?critical', text_content, re.IGNORECASE );
                    
                    critical = int( critical_match.group( 1 ) ) if critical_match else 0;
                    noncritical = int( noncritical_match.group( 1 ) ) if noncritical_match else 0;
                    
                    if date_text:
                        inspection = InspectionRecord(
                            date=date_text,
                            critical_violations=critical,
                            noncritical_violations=noncritical,
                            jurisdiction=jurisdiction_name
                        );
                        inspections.append( inspection );
                        
                except Exception as e:
                    logger.debug( f"Error parsing inspection row: {e}" );
                    continue;
            
            logger.debug( f"Parsed {len( inspections )} inspections from {jurisdiction_name}" );
            
        except Exception as e:
            logger.warning( f"Error parsing inspections: {e}" );
        
        return inspections;
    
    def _calculate_grade( self, inspections: List[InspectionRecord], jurisdiction: str ) -> HealthGrade:
        """Calculate health grade based on inspection records."""
        if not inspections:
            return HealthGrade(
                letter_grade="N/A",
                average_critical=0,
                average_noncritical=0,
                total_inspections=0,
                inspections=[],
                jurisdiction=jurisdiction,
                grade_explanation="No inspection data available"
            );
        
        total_critical = sum( i.critical_violations for i in inspections );
        total_noncritical = sum( i.noncritical_violations for i in inspections );
        
        avg_critical = total_critical / len( inspections );
        avg_noncritical = total_noncritical / len( inspections );
        
        # Calculate grade (same logic as original)
        grade_value = 0;
        
        if avg_critical >= 1:
            if avg_critical < 2:
                grade_value = 2;  # C
            elif avg_critical < 3:
                grade_value = 3;  # D
            elif avg_critical < 4:
                grade_value = 5;  # F
            else:
                grade_value = 5 + int( avg_critical - 3 );
        
        noncritical_penalty = int( avg_noncritical / 3 );
        grade_value += noncritical_penalty;
        
        grade_letters = ['A+', 'A', 'B+', 'C+', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'];
        
        if grade_value >= len( grade_letters ):
            letter_grade = f"F-{grade_value - 5}";
        else:
            letter_grade = grade_letters[grade_value];
        
        # Get last inspection date
        last_date = None;
        if inspections:
            try:
                sorted_inspections = sorted( inspections, key=lambda x: datetime.strptime( x.date, "%m/%d/%Y" ), reverse=True );
                last_date = sorted_inspections[0].date;
            except:
                last_date = inspections[0].date;
        
        explanation = f"Avg: {avg_critical:.1f} critical, {avg_noncritical:.1f} non-critical ({len( inspections )} inspections, {jurisdiction})";
        
        return HealthGrade(
            letter_grade=letter_grade,
            average_critical=avg_critical,
            average_noncritical=avg_noncritical,
            total_inspections=len( inspections ),
            inspections=inspections,
            jurisdiction=jurisdiction,
            last_inspection_date=last_date,
            grade_explanation=explanation
        );
    
    def get_health_grade( self, facility_name: str, address: str ) -> Optional[HealthGrade]:
        """
        Get health inspection grade for a restaurant across all jurisdictions.
        
        Args:
            facility_name: Name of the restaurant
            address: Full address of the restaurant
            
        Returns:
            HealthGrade object or None if not found
        """
        logger.info( f"Fetching health grade for: {facility_name}" );
        
        try:
            # Extract street name from address
            street_match = re.search( r'\d+\s+([^,]+)', address );
            street_name = street_match.group( 0 ) if street_match else None;
            
            # Detect jurisdiction from address
            primary_jurisdiction = self._detect_jurisdiction( address );
            
            # Search primary jurisdiction first
            jurisdictions_to_search = [primary_jurisdiction] if primary_jurisdiction else [];
            
            # Add other high-priority jurisdictions as fallback
            for jurisdiction in self.jurisdictions:
                if jurisdiction not in jurisdictions_to_search and jurisdiction.priority > 0:
                    jurisdictions_to_search.append( jurisdiction );
            
            # Search each jurisdiction until we find data
            for jurisdiction in jurisdictions_to_search:
                facility_url = self._search_facility( facility_name, street_name, jurisdiction );
                
                if not facility_url:
                    continue;
                
                # Fetch facility page
                self._rate_limit();
                response = self.session.get( facility_url, timeout=10 );
                response.raise_for_status();
                
                # Parse inspections
                inspections = self._parse_inspections( response.text, jurisdiction.name );
                
                if not inspections:
                    continue;
                
                # Calculate grade
                health_grade = self._calculate_grade( inspections, jurisdiction.name );
                
                logger.info( f"Health grade for {facility_name}: {health_grade.letter_grade} ({jurisdiction.name})" );
                
                return health_grade;
            
            logger.debug( f"No health inspection data found for {facility_name} in any jurisdiction" );
            return None;
            
        except Exception as e:
            logger.warning( f"Error fetching health grade for {facility_name}: {e}" );
            return None;

# Example usage
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO );
    
    client = MultiJurisdictionHealthClient();
    
    # Test KC MO restaurant
    grade = client.get_health_grade( "Joe's Kansas City", "3002 W 47th Ave Kansas City MO" );
    
    if grade:
        print( f"Grade: {grade.letter_grade}" );
        print( f"Jurisdiction: {grade.jurisdiction}" );
        print( f"Explanation: {grade.grade_explanation}" );
    else:
        print( "No data found" );
