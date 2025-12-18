#!/usr/bin/env python3
"""
Debug script to show parsed inspections vs database records side by side
"""

import sqlite3
import re
from typing import List, Dict

def get_database_inspections():
    """Get all health inspections from database"""
    conn = sqlite3.connect('data/kc_restaurants.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT establishment_name, address, critical_violations, non_critical_violations, 
               violations_desc, source_url, inspection_date, restaurant_id
        FROM health_inspections
        ORDER BY establishment_name
    ''')
    
    results = []
    for row in cursor.fetchall():
        results.append(dict(row))
    
    conn.close()
    return results

def parse_last_scrape():
    """Parse the last scraped HTML file"""
    try:
        with open('logs/article_jackson_county_health_inspections_blue_springs_nov_12_to_18.html', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("No HTML dump found. Run the scraper first.")
        return []
    
    # Extract text content from HTML (remove tags)
    text = re.sub(r'<[^>]+>', '', content)
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'\r', '', text)
    
    # Parse using the same logic as examiner_scraper.py
    inspections = []
    
    # Pattern: "Name: Address, inspected Date"
    header_pattern = re.compile(
        r'^(?P<name>.+?):\s+(?P<address>.+?),\s+inspected\s+(?P<date>.*?)(?:\.|$)',
        re.IGNORECASE
    )
    
    lines = text.split('\n')
    current_inspection = None
    current_violations = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new restaurant
        match = header_pattern.match(line)
        if match:
            # Save previous inspection if exists
            if current_inspection:
                current_inspection['violations_desc'] = "\n".join(current_violations)
                viol_count = len([v for v in current_violations if v])
                crit_count = len([v for v in current_violations if "Corrected" in v])
                current_inspection['critical_violations'] = crit_count
                current_inspection['non_critical_violations'] = max(0, viol_count - crit_count)
                inspections.append(current_inspection)
            
            # Start new inspection
            name = match.group('name').strip()
            # Filter out noise
            if "Health Inspections" in name or len(name) > 100:
                current_inspection = None
                current_violations = []
                continue
                
            current_inspection = {
                'establishment_name': name,
                'address': match.group('address').strip(),
                'inspection_date_text': match.group('date').strip()
            }
            current_violations = []
        elif current_inspection:
            # Skip UI text
            if line.upper() in ["LOGOUT", "HOME", "NEWS", "CONTACT US"]:
                continue
            current_violations.append(line)
    
    # Save last inspection
    if current_inspection:
        current_inspection['violations_desc'] = "\n".join(current_violations)
        viol_count = len([v for v in current_violations if v])
        crit_count = len([v for v in current_violations if "Corrected" in v])
        current_inspection['critical_violations'] = crit_count
        current_inspection['non_critical_violations'] = max(0, viol_count - crit_count)
        inspections.append(current_inspection)
        
    return inspections

def main():
    print("=" * 120)
    print("HEALTH INSPECTION DATA COMPARISON")
    print("=" * 120)
    
    # Get data from both sources
    db_inspections = get_database_inspections()
    parsed_inspections = parse_last_scrape()
    
    print(f"\nDatabase Records: {len(db_inspections)}")
    print(f"Parsed from HTML: {len(parsed_inspections)}")
    
    # Create a lookup dict for database records
    db_lookup = {insp['establishment_name']: insp for insp in db_inspections}
    
    print("\n" + "=" * 120)
    print(f"{'ESTABLISHMENT NAME':<35} | {'ADDRESS':<30} | {'CRIT':<4} | {'NON-C':<5} | {'IN DB?':<6}")
    print("-" * 120)
    
    # Show parsed inspections
    for parsed in parsed_inspections:
        name = parsed['establishment_name']
        addr = parsed['address'][:28] + '..' if len(parsed['address']) > 30 else parsed['address']
        crit = parsed['critical_violations']
        non_crit = parsed['non_critical_violations']
        
        # Check if exists in DB
        in_db = "YES" if name in db_lookup else "NO"
        
        print(f"{name[:33]:<35} | {addr:<30} | {crit:>4} | {non_crit:>5} | {in_db:<6}")
        
        # If in DB, show comparison
        if name in db_lookup:
            db_rec = db_lookup[name]
            if db_rec['critical_violations'] != crit or db_rec['non_critical_violations'] != non_crit:
                print(f"  └─> DB VALUES: crit={db_rec['critical_violations']}, non-crit={db_rec['non_critical_violations']} [MISMATCH!]")
    
    # Show any DB records not in parsed list
    print("\n" + "=" * 120)
    print("DATABASE RECORDS NOT FOUND IN LATEST PARSE:")
    print("-" * 120)
    
    parsed_names = {p['establishment_name'] for p in parsed_inspections}
    orphaned = [db for db in db_inspections if db['establishment_name'] not in parsed_names]
    
    if orphaned:
        for orph in orphaned:
            print(f"  - {orph['establishment_name']}: {orph['address']} (crit={orph['critical_violations']}, non-crit={orph['non_critical_violations']})")
    else:
        print("  None - all DB records match parsed data")
    
    # Show violation details for first 3 records
    print("\n" + "=" * 120)
    print("SAMPLE VIOLATION DESCRIPTIONS (First 3):")
    print("-" * 120)
    
    for i, parsed in enumerate(parsed_inspections[:3]):
        print(f"\n{i+1}. {parsed['establishment_name']}")
        print(f"   Address: {parsed['address']}")
        print(f"   Violations ({parsed['critical_violations']} crit, {parsed['non_critical_violations']} non-crit):")
        
        violations = parsed.get('violations_desc', '').split('\n')
        for v in violations[:5]:  # Show first 5 violations
            if v.strip():
                print(f"     - {v.strip()[:100]}")
        if len(violations) > 5:
            print(f"     ... and {len(violations)-5} more")

if __name__ == "__main__":
    main()