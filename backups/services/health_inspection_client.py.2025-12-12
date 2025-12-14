#!/usr/bin/env python3
"""
Kansas City Health Inspection Client
Fetches and grades restaurants based on health inspection data from inspectionsonline.us
"""

import requests;
import re;
import logging;
import time;
from typing import List, Dict, Optional, Tuple;
from dataclasses import dataclass;
from datetime import datetime;
from bs4 import BeautifulSoup;

logger = logging.getLogger( __name__ );

@dataclass
class InspectionRecord:
    """Single inspection record."""
    date: str;
    critical_violations: int;
    noncritical_violations: int;
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
    last_inspection_date: Optional[str] = None;
    grade_explanation: Optional[str] = None;

class HealthInspectionClient:
    """Client for fetching KC health inspection data."""
    
    def __init__( self, rate_limit_delay: float = 1.0 ):
        """
        Initialize health inspection client.
        
        Args:
            rate_limit_delay: Delay between requests in seconds (default: 1.0)
        """
        self.base_url = "https://www.inspectionsonline.us/mo/usakansascity/inspect.nsf";
        self.search_url = f"{self.base_url}/Search?OpenForm";
        self.rate_limit_delay = rate_limit_delay;
        self.session = requests.Session();
        self.session.headers.update( {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        } );
        self.last_request_time = 0;
        
        logger.info( f"Health inspection client initialized (rate_limit: {rate_limit_delay}s)" );
    
    def _rate_limit( self ):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time;
        if elapsed < self.rate_limit_delay:
            time.sleep( self.rate_limit_delay - elapsed );
        self.last_request_time = time.time();
    
    def _search_facility( self, facility_name: str, street_name: Optional[str] = None ) -> Optional[str]:
        """
        Search for a facility and return the inspection results URL.
        
        Args:
            facility_name: Name of the restaurant
            street_name: Optional street name to narrow search
            
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
            
            logger.debug( f"Searching for facility: {facility_name}" + ( f" on {street_name}" if street_name else "" ) );
            
            response = self.session.post( self.search_url, data=search_params, timeout=10 );
            response.raise_for_status();
            
            soup = BeautifulSoup( response.text, 'html.parser' );
            
            # Look for results link - facility names are typically in links
            results_links = soup.find_all( 'a', href=re.compile( r'Facility\?OpenDocument' ) );
            
            if results_links:
                # Get first match
                first_link = results_links[0];
                facility_url = first_link.get( 'href' );
                
                # Make URL absolute
                if not facility_url.startswith( 'http' ):
                    facility_url = self.base_url + '/' + facility_url.lstrip( '/' );
                
                logger.debug( f"Found facility URL: {facility_url}" );
                return facility_url;
            
            logger.debug( f"No facility found for: {facility_name}" );
            return None;
            
        except Exception as e:
            logger.warning( f"Error searching for facility {facility_name}: {e}" );
            return None;
    
    def _parse_inspections( self, html_content: str ) -> List[InspectionRecord]:
        """
        Parse inspection records from facility page HTML.
        
        Args:
            html_content: HTML content of facility page
            
        Returns:
            List of InspectionRecord objects
        """
        inspections = [];
        
        try:
            soup = BeautifulSoup( html_content, 'html.parser' );
            
            # Find inspection links/rows
            inspection_links = soup.find_all( 'a', href=re.compile( r'Inspection\?OpenDocument' ) );
            
            for link in inspection_links:
                try:
                    # Parse inspection data from link text or nearby elements
                    parent_row = link.find_parent( 'tr' );
                    if not parent_row:
                        continue;
                    
                    cells = parent_row.find_all( 'td' );
                    
                    if len( cells ) < 3:
                        continue;
                    
                    # Extract date, critical, non-critical counts
                    date_text = cells[0].get_text( strip=True ) if len( cells ) > 0 else "";
                    
                    # Look for violation counts - these may be in different formats
                    text_content = parent_row.get_text();
                    
                    # Try to extract critical and non-critical violation counts
                    critical_match = re.search( r'(\d+)\s*critical', text_content, re.IGNORECASE );
                    noncritical_match = re.search( r'(\d+)\s*non-?critical', text_content, re.IGNORECASE );
                    
                    critical = int( critical_match.group( 1 ) ) if critical_match else 0;
                    noncritical = int( noncritical_match.group( 1 ) ) if noncritical_match else 0;
                    
                    if date_text:
                        inspection = InspectionRecord(
                            date=date_text,
                            critical_violations=critical,
                            noncritical_violations=noncritical
                        );
                        inspections.append( inspection );
                        
                except Exception as e:
                    logger.debug( f"Error parsing inspection row: {e}" );
                    continue;
            
            # Alternative parsing: look for inspection detail pages
            if not inspections:
                # Try clicking through to get detailed inspection data
                for link in inspection_links[:5]:  # Limit to most recent 5
                    try:
                        inspection_url = link.get( 'href' );
                        if not inspection_url.startswith( 'http' ):
                            inspection_url = self.base_url + '/' + inspection_url.lstrip( '/' );
                        
                        self._rate_limit();
                        detail_response = self.session.get( inspection_url, timeout=10 );
                        detail_response.raise_for_status();
                        
                        detail_soup = BeautifulSoup( detail_response.text, 'html.parser' );
                        
                        # Extract violation counts from detail page
                        date_elem = detail_soup.find( text=re.compile( r'Inspection Date', re.IGNORECASE ) );
                        date = "";
                        if date_elem:
                            date_parent = date_elem.find_parent();
                            if date_parent:
                                date = date_parent.get_text().split( ':' )[-1].strip();
                        
                        # Count critical and non-critical violations
                        critical = len( detail_soup.find_all( text=re.compile( r'Critical', re.IGNORECASE ) ) );
                        noncritical = len( detail_soup.find_all( text=re.compile( r'Non-Critical', re.IGNORECASE ) ) );
                        
                        if date or critical > 0 or noncritical > 0:
                            inspection = InspectionRecord(
                                date=date or "Unknown",
                                critical_violations=critical,
                                noncritical_violations=noncritical
                            );
                            inspections.append( inspection );
                            
                    except Exception as e:
                        logger.debug( f"Error fetching inspection details: {e}" );
                        continue;
            
            logger.debug( f"Parsed {len( inspections )} inspection records" );
            
        except Exception as e:
            logger.warning( f"Error parsing inspections: {e}" );
        
        return inspections;
    
    def _calculate_grade( self, inspections: List[InspectionRecord] ) -> HealthGrade:
        """
        Calculate health grade based on inspection records.
        
        Grading scheme:
        - Start at A
        - 1 critical violation = C
        - 2 critical violations = D
        - 3 critical violations = F
        - 4+ critical violations = continue past F (G, H, etc.)
        - Every 3 non-critical violations = minus one letter grade
        - Every 6 non-critical violations = minus two letter grades
        
        Grades are averaged across all inspections.
        
        Args:
            inspections: List of inspection records
            
        Returns:
            HealthGrade object with calculated grade
        """
        if not inspections:
            return HealthGrade(
                letter_grade="N/A",
                average_critical=0,
                average_noncritical=0,
                total_inspections=0,
                inspections=[],
                grade_explanation="No inspection data available"
            );
        
        total_critical = sum( i.critical_violations for i in inspections );
        total_noncritical = sum( i.noncritical_violations for i in inspections );
        
        avg_critical = total_critical / len( inspections );
        avg_noncritical = total_noncritical / len( inspections );
        
        # Calculate grade based on averages
        # Start with A (grade value 0)
        grade_value = 0;
        
        # Apply critical violations penalty
        if avg_critical >= 1:
            if avg_critical < 2:
                grade_value = 2;  # C
            elif avg_critical < 3:
                grade_value = 3;  # D
            elif avg_critical < 4:
                grade_value = 5;  # F
            else:
                # Continue past F
                grade_value = 5 + int( avg_critical - 3 );
        
        # Apply non-critical violations penalty
        # Every 3 non-critical = -1 grade
        noncritical_penalty = int( avg_noncritical / 3 );
        grade_value += noncritical_penalty;
        
        # Convert grade value to letter
        grade_letters = ['A+', 'A', 'B+', 'C+', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'];
        
        if grade_value >= len( grade_letters ):
            letter_grade = f"F-{grade_value - 5}";  # F-1, F-2, etc.
        else:
            letter_grade = grade_letters[grade_value];
        
        # Get last inspection date
        last_date = None;
        if inspections:
            # Sort by date if possible, otherwise just take first
            try:
                sorted_inspections = sorted( inspections, key=lambda x: datetime.strptime( x.date, "%m/%d/%Y" ), reverse=True );
                last_date = sorted_inspections[0].date;
            except:
                last_date = inspections[0].date;
        
        # Generate explanation
        explanation = f"Avg: {avg_critical:.1f} critical, {avg_noncritical:.1f} non-critical violations across {len( inspections )} inspection(s)";
        
        return HealthGrade(
            letter_grade=letter_grade,
            average_critical=avg_critical,
            average_noncritical=avg_noncritical,
            total_inspections=len( inspections ),
            inspections=inspections,
            last_inspection_date=last_date,
            grade_explanation=explanation
        );
    
    def get_health_grade( self, facility_name: str, address: str ) -> Optional[HealthGrade]:
        """
        Get health inspection grade for a restaurant.
        
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
            
            # Search for facility
            facility_url = self._search_facility( facility_name, street_name );
            
            if not facility_url:
                logger.debug( f"No health inspection data found for {facility_name}" );
                return None;
            
            # Fetch facility page
            self._rate_limit();
            response = self.session.get( facility_url, timeout=10 );
            response.raise_for_status();
            
            # Parse inspections
            inspections = self._parse_inspections( response.text );
            
            if not inspections:
                logger.debug( f"No inspection records found for {facility_name}" );
                return None;
            
            # Calculate grade
            health_grade = self._calculate_grade( inspections );
            
            logger.info( f"Health grade for {facility_name}: {health_grade.letter_grade} ({health_grade.total_inspections} inspections)" );
            
            return health_grade;
            
        except Exception as e:
            logger.warning( f"Error fetching health grade for {facility_name}: {e}" );
            return None;

# Example usage
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO );
    
    client = HealthInspectionClient();
    
    # Test with known restaurant
    grade = client.get_health_grade( "Joe's Kansas City", "3002 W 47th Ave" );
    
    if grade:
        print( f"Grade: {grade.letter_grade}" );
        print( f"Explanation: {grade.grade_explanation}" );
        print( f"Last inspection: {grade.last_inspection_date}" );
    else:
        print( "No data found" );
