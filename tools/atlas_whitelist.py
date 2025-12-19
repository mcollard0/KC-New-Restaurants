#!/usr/bin/env python3
"""
MongoDB Atlas IP Whitelist Tool
Adds the current IP address to your MongoDB Atlas Project's Network Access list.

Usage:
    python3 tools/atlas_whitelist.py --public-key <PUB> --private-key <PRIV> --project-id <ID>
    
    OR using environment variables:
    export ATLAS_PUBLIC_KEY="..."
    export ATLAS_PRIVATE_KEY="..."
    export ATLAS_PROJECT_ID="..."
    python3 tools/atlas_whitelist.py
"""

import os
import sys
import argparse
import requests
from requests.auth import HTTPDigestAuth

def get_current_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        return response.json()['ip']
    except Exception as e:
        print(f"Error getting current IP: {e}")
        return None

def add_ip_to_whitelist(public_key, private_key, project_id, ip_address, comment="Added via script"):
    url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{project_id}/accessList"
    
    payload = [{
        "ipAddress": ip_address,
        "comment": comment
    }]
    
    print(f"Adding IP {ip_address} to Project {project_id}...")
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=HTTPDigestAuth(public_key, private_key),
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ Success! IP added to whitelist.")
            return True
        elif response.status_code == 200:
            print("ℹ️  IP already whitelisted (or updated).")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error calling Atlas API: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Whitelist current IP in MongoDB Atlas')
    parser.add_argument('--public-key', help='Atlas Public API Key')
    parser.add_argument('--private-key', help='Atlas Private API Key')
    parser.add_argument('--project-id', help='Atlas Project ID')
    
    args = parser.parse_args()
    
    # Get credentials from args or env
    pub = args.public_key or os.getenv('ATLAS_PUBLIC_KEY')
    priv = args.private_key or os.getenv('ATLAS_PRIVATE_KEY')
    pid = args.project_id or os.getenv('ATLAS_PROJECT_ID')
    
    if not all([pub, priv, pid]):
        print("Error: Missing credentials.")
        print("Please provide --public-key, --private-key, and --project-id")
        print("OR set ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY, and ATLAS_PROJECT_ID env vars.")
        sys.exit(1)
        
    current_ip = get_current_ip()
    if not current_ip:
        print("Could not determine public IP. Exiting.")
        sys.exit(1)
        
    print(f"Current Public IP: {current_ip}")
    
    add_ip_to_whitelist(pub, priv, pid, current_ip)

if __name__ == "__main__":
    main()
