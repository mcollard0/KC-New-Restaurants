#!/usr/bin/env python3
"""
Database dump tool for health inspections with search capabilities
Usage: 
    python dump_records.py
    python dump_records.py search=Wendy
    python dump_records.py query="Nov. 12 to 18"
    python dump_records.py find=critical
"""

import sqlite3
import sys
import os
import re
from typing import List, Dict, Optional

def get_database_path():
    """Get the database path relative to script location"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, '..', 'data', 'kc_restaurants.db')

def get_health_inspections(search_term: Optional[str] = None) -> List[Dict]:
    """Get all health inspections from database with optional search"""
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if search_term:
        # Search across multiple fields
        search_pattern = f'%{search_term}%'
        cursor.execute('''
            SELECT id, establishment_name, address, critical_violations, non_critical_violations, 
                   violations_desc, source_url, inspection_date, inspection_date_range, 
                   restaurant_id, created_at
            FROM health_inspections
            WHERE establishment_name LIKE ? 
               OR address LIKE ?
               OR violations_desc LIKE ?
               OR inspection_date_range LIKE ?
               OR inspection_type LIKE ?
            ORDER BY establishment_name, inspection_date_range
        ''', (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
    else:
        cursor.execute('''
            SELECT id, establishment_name, address, critical_violations, non_critical_violations, 
                   violations_desc, source_url, inspection_date, inspection_date_range, 
                   restaurant_id, created_at
            FROM health_inspections
            ORDER BY establishment_name, inspection_date_range
        ''')
    
    results = []
    for row in cursor.fetchall():
        results.append(dict(row))
    
    conn.close()
    return results

def format_violations(violations_desc: str, max_lines: int = 5) -> List[str]:
    """Format violations description for display"""
    if not violations_desc:
        return []
    
    lines = violations_desc.split('\n')
    formatted = []
    for i, line in enumerate(lines[:max_lines]):
        line = line.strip()
        if line:
            # Truncate long lines
            if len(line) > 100:
                line = line[:97] + "..."
            formatted.append(f"     {i+1}. {line}")
    
    if len(lines) > max_lines:
        formatted.append(f"     ... and {len(lines) - max_lines} more violations")
    
    return formatted

def display_inspections(inspections: List[Dict], verbose: bool = False):
    """Display inspections in a formatted way"""
    if not inspections:
        print("No inspection records found.")
        return
    
    print("\n" + "=" * 120)
    print(f"HEALTH INSPECTION RECORDS ({len(inspections)} total)")
    print("=" * 120)
    
    for i, insp in enumerate(inspections, 1):
        print(f"\n{i}. {insp['establishment_name']}")
        print(f"   Address: {insp['address']}")
        print(f"   Date Range: {insp['inspection_date_range']}")
        print(f"   Violations: {insp['critical_violations']} critical, {insp['non_critical_violations']} non-critical")
        
        # Calculate grade based on violations (similar to health_inspection_client.py logic)
        crit = insp['critical_violations']
        non_crit = insp['non_critical_violations']
        
        if crit == 0 and non_crit == 0:
            grade = "A"
        elif crit == 0 and non_crit <= 3:
            grade = "B"
        elif crit == 1 or (crit == 0 and non_crit <= 6):
            grade = "C"
        elif crit == 2 or (crit == 1 and non_crit > 3):
            grade = "D"
        else:
            grade = "F"
        
        # Adjust for non-critical violations (every 3 non-critical = -1 letter grade)
        if non_crit >= 9:
            grade_adjust = non_crit // 3
            grade_ord = ord(grade) + grade_adjust
            if grade_ord > ord('F'):
                grade = 'F'
            else:
                grade = chr(grade_ord)
        
        print(f"   Calculated Grade: {grade}")
        
        if verbose or i <= 3:  # Show details for first 3 or all if verbose
            print(f"   Violations Detail:")
            violation_lines = format_violations(insp['violations_desc'])
            for line in violation_lines:
                print(line)
        
        if insp['restaurant_id']:
            print(f"   Linked to Restaurant ID: {insp['restaurant_id']}")
        
        print(f"   Source: {insp['source_url']}")
        print(f"   Record ID: {insp['id']} | Created: {insp['created_at']}")

def main():
    """Main entry point"""
    search_term = None
    verbose = False
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        # Check for search patterns
        if '=' in arg:
            key, value = arg.split('=', 1)
            if key.lower() in ['search', 'query', 'find']:
                search_term = value
                print(f"Searching for: '{search_term}'")
        elif arg.lower() in ['-v', '--verbose']:
            verbose = True
        else:
            # Treat as search term directly
            search_term = arg
            print(f"Searching for: '{search_term}'")
    
    # Get and display inspections
    inspections = get_health_inspections(search_term)
    display_inspections(inspections, verbose)
    
    # Summary
    print("\n" + "-" * 120)
    if search_term:
        print(f"Found {len(inspections)} inspection records matching '{search_term}'")
    else:
        print(f"Total inspection records: {len(inspections)}")
    
    # Show unique establishments
    unique_establishments = set(insp['establishment_name'] for insp in inspections)
    print(f"Unique establishments: {len(unique_establishments)}")
    
    # Show date ranges
    date_ranges = set(insp['inspection_date_range'] for insp in inspections if insp['inspection_date_range'])
    if date_ranges:
        print(f"Date ranges covered: {', '.join(sorted(date_ranges))}")

if __name__ == "__main__":
    main()