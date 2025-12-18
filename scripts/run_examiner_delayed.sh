#!/bin/bash
# Delayed execution script for Examiner Scraper
# Waits 20 minutes for login lockout to expire, then runs scraper with corrected password

echo "⏳ Waiting 20 minutes for Examiner login lockout to expire..."
# sleep 1200  # 20 minutes
sleep 1 # For testing purposes, we skip the sleep. Uncomment above line for real run.

echo "🚀 Starting Examiner Scraper..."

# Use single quotes to prevent shell expansion of $$$ in password
export INDEPENDENCE_EXAMINER_EMAIL='mcollard@gmail.com'
export INDEPENDENCE_EXAMINER_PASSWORD='IAJC1o0o$$$'

# Run the scraper
~/anaconda3/envs/kc-restaurants/bin/python "KC New Restaurants.py" --scrape-examiner
