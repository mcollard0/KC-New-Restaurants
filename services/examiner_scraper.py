#!/usr/bin/env python3
"""
Examiner Scraper Service
Scrapes health inspection data from The Independence Examiner using Playwright
"""

import os
import re
import logging
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)
class ExaminerScraper:
    def __init__(self, db_manager=None, debug_mode=False):
        self.base_url = "https://www.examiner.net"
        self.login_url = f"{self.base_url}/login/"
        
        self.username = os.getenv('INDEPENDENCE_EXAMINER_EMAIL')
        self.password = os.getenv('INDEPENDENCE_EXAMINER_PASSWORD')
        
        self.db_manager = db_manager
        self.debug_mode = debug_mode
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def start_browser(self):
        """Initialize Playwright browser with persistent context"""
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            
            # Create a context with specific user agent
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/Chicago"
            )
            self.page = self.context.new_page()
            
            # Apply stealth
            Stealth().apply_stealth_sync(self.page)
            logger.info("Playwright stealth applied")

    def close_browser(self):
        """Close browser resources"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def random_delay(self, min_seconds=2, max_seconds=5):
        """Sleep for a random amount of time to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"Waiting {delay:.2f}s...")
        time.sleep(delay)

    def login(self) -> bool:
        """Attempt to login to The Examiner using Playwright"""
        if not self.username or not self.password:
            logger.warning("Credentials not found in environment")
            return False

        logger.info(f"Attempting login as {self.username}...")
        if self.password:
            logger.info(f"Password length: {len(self.password)}, ends with: {self.password[-3:]}")
        
        try:
            if not self.page:
                self.start_browser()

            logger.info(f"Navigating to {self.login_url}")
            self.page.goto(self.login_url)
            self.random_delay(2, 4)
            
            # Wait for form
            self.page.wait_for_selector("#user_login")
            self.random_delay(1, 2)
            
            # Fill credentials with typing delay
            logger.info("Filling credentials...")
            self.page.type("#user_login", self.username, delay=random.randint(50, 150))
            self.random_delay(0.5, 1.5)
            self.page.type("#user_pass", self.password, delay=random.randint(50, 150))
            self.random_delay(1, 2)
            
            # Click login with delay
            logger.info("Submitting login form...")
            self.page.click("#wp-submit")
            
            # Wait for navigation
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(3000) # Extra wait for redirects
            
            logger.info(f"Page URL after login submission: {self.page.url}")
            
            # Check for success
            # Usually redirects to wp-admin or home, or shows "Log Out"
            is_logged_in = False
            
            # Check for admin bar or logout link
            try:
                if self.page.query_selector("text=Log Out") or self.page.query_selector("#wpadminbar"):
                    is_logged_in = True
            except:
                pass
                
            if "wp-login.php" not in self.page.url and self.page.url != self.login_url:
                 # We moved away from login page
                 is_logged_in = True

            if is_logged_in:
                logger.info("Login successful (verified)")
                
                # Debug: Check cookies
                cookies = self.context.cookies()
                logger.info(f"Cookies after login: {len(cookies)} found")
                for c in cookies:
                    if 'wordpress' in c['name']:
                        logger.info(f"  Cookie: {c['name']}")
                        
                return True
            
            # Check for error
            error_element = self.page.query_selector(".login-error, #login_error, .message-error")
            if error_element:
                error_text = error_element.inner_text()
                logger.error(f"Login failed: {error_text}")
            else:
                logger.warning(f"Login failed (unknown reason). URL: {self.page.url}")
                # Dump for debug
                self.dump_html(self.page.content(), "login_failed.html")
                
            return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def find_articles(self) -> List[Dict]:
        """Find health inspection articles from the news category"""
        url = f"{self.base_url}/category/news/"
        logger.info(f"Scanning {url}")
        
        self.random_delay(3, 6)
        
        articles = []
        try:
            try:
                # Try navigating with a different wait condition or catching the abort
                # ERR_ABORTED usually happens when a client-side script redirects the page immediately
                # or cancels the loading. We proceed as long as we have access to the page context.
                response = self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                status_code = response.status if response else "No Response"
                logger.info(f"Navigation response status: {status_code}")
                
                if response:
                    # Log relevant headers
                    headers = response.headers
                    logger.info(f"Response Headers: {headers}")
                    
                    # Check for server-side error messages in headers
                    if 'x-error' in headers:
                        logger.warning(f"Found x-error header: {headers['x-error']}")

            except Exception as e:
                logger.warning(f"Navigation to category page reported error (likely ERR_ABORTED): {e}")
                logger.info(f"Current URL after error: {self.page.url}")
                
                try:
                    page_title = self.page.title()
                    logger.info(f"Page Title after error: {page_title}")
                    
                    # Check for common error texts in the HTML head/body
                    content = self.page.content()
                    
                    # Look for error messages in H1 or title
                    if "403 Forbidden" in content or "Access Denied" in content:
                        logger.error("Detected 403 Forbidden / Access Denied in content")
                    
                    # Dump content to see where we are
                    self.dump_html(content, "category_page_error.html")
                except Exception as dump_e:
                    logger.error(f"Failed to inspect page after error: {dump_e}")
            
            # Wait a bit for any client-side redirects or checks
            self.random_delay(3, 5)
            
            # Dump content for debugging
            if self.debug_mode:
                 self.dump_html(self.page.content(), "category_page_scan.html")

            # Get all links
            links = self.page.query_selector_all("a[href]")
            
            for link in links:
                title = link.inner_text().strip()
                href = link.get_attribute("href")
                
                if not title or not href:
                    continue
                    
                # Regex for "Health Inspection" or similar
                if re.search(r'health\s*inspection', title, re.IGNORECASE):
                    # Dedup
                    if not any(a['url'] == href for a in articles):
                        articles.append({
                            'title': title,
                            'url': href,
                            'date': datetime.now().strftime('%Y-%m-%d') # Default
                        })
            
            logger.info(f"Found {len(articles)} health inspection articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error scanning articles: {e}")
            return []

    def dump_html(self, content: str, filename: str):
        """Dump HTML content to a file for debugging"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            filepath = os.path.join(log_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Dumped HTML to {filepath}")
        except Exception as e:
            logger.error(f"Failed to dump HTML: {e}")

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch content of a single article"""
        logger.info(f"Fetching article: {url}")
        self.random_delay(3, 6)
        
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Check login status on the article page
            if "Log Out" in self.page.content() or "wp-admin" in self.page.content():
                 logger.info("Verified: Still logged in on article page")
            else:
                 logger.warning("Warning: Login indicator not found on article page. Session might be lost.")
                 # Log cookies to see if they are still there
                 cookies = self.context.cookies()
                 logger.info(f"Cookies present: {len(cookies)}")

            # Scroll to bottom to trigger lazy loading
            logger.info("Scrolling page...")
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(2000)
            
            # Debug: Dump content
            if self.debug_mode:
                html_content = self.page.content()
                safe_name = re.sub(r'[^a-zA-Z0-9]', '_', url.split('/')[-2] if url.endswith('/') else url.split('/')[-1])
                self.dump_html(html_content, f"article_{safe_name}.html")
                logger.info(f"--- RAW HTML SNIPPET (First 1000 chars) ---\n{html_content[:1000]}\n------------------------------------------")
            
            # Look for content
            # Try standard WordPress content areas
            content_selectors = [".entry-content", "article", ".post-content"]
            
            content_text = ""
            for selector in content_selectors:
                element = self.page.query_selector(selector)
                if element:
                    content_text = element.inner_text()
                    break
            
            if not content_text:
                logger.warning("Specific content area not found, using full page text")
                content_text = self.page.inner_text("body")
            
            if not content_text:
                logger.warning("Could not find any text content")
                return None
                
            return content_text
            
        except Exception as e:
            logger.error(f"Error fetching article {url}: {e}")
            return None

    def parse_inspections(self, text: str, inspection_type: str = "General") -> List[Dict]:
        """
        Parse raw text into structured inspection data using multiple patterns
        """
        inspections = []
        
        # Simplify text: normalize whitespace but keep newlines for line-based parsing
        clean_text = re.sub(r'\xa0', ' ', text)
        clean_text = re.sub(r'\r', '', clean_text)
        
        # Strategy 1: Look for explicit "X critical, Y non-critical" summaries
        # Pattern: "Name, Address: X critical... Y non-critical"
        summary_pattern = re.compile(
            r'(?P<name>[\w\s’\'\.-]+?),\s*(?P<address>[\w\s\.,-]+?):\s*(?P<crit>\d+)\s*critical.*?(?P<noncrit>\d+)\s*non-?critical', 
            re.DOTALL | re.IGNORECASE | re.UNICODE
        )
        
        summary_matches = list(summary_pattern.finditer(clean_text))
        
        if summary_matches:
            logger.info(f"Found {len(summary_matches)} inspections using summary pattern")
            for match in summary_matches:
                name = match.group('name').strip()
                if len(name) > 100 or "Copyright" in name or "Subscribe" in name:
                    continue
                    
                inspection = {
                    'establishment_name': name,
                    'address': match.group('address').strip(),
                    'critical_violations': int(match.group('crit')),
                    'non_critical_violations': int(match.group('noncrit')),
                    'violations_desc': match.group(0).strip(),
                    'inspection_type': inspection_type
                }
                inspections.append(inspection)
            return inspections
            
        # Strategy 2: Line-by-line parsing for "Name: Address, inspected Date" format
        logger.info("No summary matches found, trying detailed format parsing")
        
        # Pattern: "Name: Address, inspected Date"
        # e.g. "Wendy’s: 310 NW Missouri 7, inspected Nov. 12."
        header_pattern = re.compile(
            r'^(?P<name>.+?):\s+(?P<address>.+?),\s+inspected\s+(?P<date>.*?)(?:\.|$)',
            re.IGNORECASE
        )
        
        lines = clean_text.split('\n')
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
                    # Count violations (approximate)
                    # Count lines that start with "Observed" or seem to be descriptions
                    viol_count = len([v for v in current_violations if v])
                    # Simple heuristic: "Corrected" usually implies critical/priority
                    crit_count = len([v for v in current_violations if "Corrected" in v])
                    current_inspection['critical_violations'] = crit_count
                    current_inspection['non_critical_violations'] = max(0, viol_count - crit_count)
                    inspections.append(current_inspection)
                
                # Start new inspection
                name = match.group('name').strip()
                # Filter out noise (e.g. "Jackson County Health Inspections: ...")
                if "Health Inspections" in name or len(name) > 100:
                    current_inspection = None
                    current_violations = []
                    continue
                    
                current_inspection = {
                    'establishment_name': name,
                    'address': match.group('address').strip(),
                    'inspection_type': inspection_type,
                    'inspection_date_text': match.group('date').strip()
                }
                current_violations = []
            elif current_inspection:
                # Append to current inspection's violations
                # Skip some common UI text if it sneaks in
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

    def calculate_levenshtein(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        Returns the minimum number of single-character edits required to change s1 into s2.
        """
        if len(s1) < len(s2):
            return self.calculate_levenshtein(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def link_to_restaurant(self, inspection: Dict) -> Optional[int]:
        """
        Link inspection to existing restaurant ID in DB using Levenshtein distance
        """
        if not self.db_manager:
            return None
            
        conn = self.db_manager.sqlite_conn
        cursor = conn.cursor()
        
        # Fetch all restaurants for comparison (caching could be added if list grows large)
        cursor.execute('SELECT id, business_name, dba_name FROM food_businesses')
        restaurants = cursor.fetchall()
        
        target_name = inspection['establishment_name'].upper()
        # Clean target name (remove common suffixes for better matching)
        target_clean = re.sub(r'\s+(LLC|INC|CORP)\b', '', target_name, flags=re.IGNORECASE).strip()
        
        best_match_id = None
        min_distance = float('inf')
        
        for r_id, b_name, dba_name in restaurants:
            candidates = []
            if b_name: candidates.append(b_name.upper())
            if dba_name: candidates.append(dba_name.upper())
            
            for candidate in candidates:
                # Clean candidate
                candidate_clean = re.sub(r'\s+(LLC|INC|CORP)\b', '', candidate, flags=re.IGNORECASE).strip()
                
                # Calculate distance
                dist = self.calculate_levenshtein(target_clean, candidate_clean)
                
                # Normalize distance by length (0.0 to 1.0, where 0.0 is perfect match)
                max_len = max(len(target_clean), len(candidate_clean))
                if max_len == 0: continue
                
                normalized_dist = dist / max_len
                
                if normalized_dist < min_distance:
                    min_distance = normalized_dist
                    best_match_id = r_id

        # Threshold: Allow up to 20% difference (0.2)
        # e.g., "McDonalds" vs "McDonald's" is very close
        if min_distance <= 0.2:
            if self.debug_mode:
                print(f"  Matched '{target_name}' to ID {best_match_id} (Score: {1.0 - min_distance:.2f})")
            return best_match_id
            
        return None

    def save_inspections(self, inspections: List[Dict], source_url: str):
        """Save inspections to database"""
        if not self.db_manager:
            return

        conn = self.db_manager.sqlite_conn
        cursor = conn.cursor()
        
        count = 0
        for insp in inspections:
            # Check if duplicate (same name, date, violations)
            # We don't have exact date in regex yet, using import date
            cursor.execute('''
                SELECT id FROM health_inspections 
                WHERE establishment_name = ? AND source_url = ?
            ''', (insp['establishment_name'], source_url))
            
            if cursor.fetchone():
                continue # Skip duplicate
            
            # Find restaurant ID
            restaurant_id = self.link_to_restaurant(insp)
            
            cursor.execute('''
                INSERT INTO health_inspections 
                (establishment_name, address, critical_violations, non_critical_violations, 
                 violations_desc, source_url, inspection_type, inspection_date, restaurant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                insp['establishment_name'],
                insp['address'],
                insp['critical_violations'],
                insp['non_critical_violations'],
                insp['violations_desc'],
                source_url,
                insp['inspection_type'],
                datetime.now().strftime('%Y-%m-%d'), # Approximation
                restaurant_id
            ))
            count += 1
        
        conn.commit()
        if self.debug_mode:
            print(f"Saved {count} new inspections from {source_url}")

    def run(self):
        """Main execution method"""
        if self.debug_mode:
            print("Starting Examiner Scraper...")
            
        try:
            self.login()
            
            articles = self.find_articles()
            if self.debug_mode:
                print(f"Found {len(articles)} articles to process.")
                
            for article in articles:
                if self.debug_mode:
                    print(f"Processing: {article['title']}")
                    
                content = self.fetch_article_content(article['url'])
                if content:
                    # Determine inspection type from title
                    insp_type = "General"
                    if "Independence" in article['title']:
                        insp_type = "Independence"
                    elif "Jackson" in article['title']:
                        insp_type = "Jackson County"
                    elif "Blue Springs" in article['title']:
                        insp_type = "Blue Springs"
                        
                inspections = self.parse_inspections(content, insp_type)
                
                if self.debug_mode:
                    if not inspections:
                        logger.warning("No inspections found in text. Dumping snippet for regex debugging:")
                        # Find relevant section
                        start_idx = content.find("Critical violations")
                        if start_idx == -1: start_idx = 0
                        snippet = content[start_idx:start_idx+2000]
                        print(f"--- TEXT SNIPPET ---\n{snippet}\n--------------------")
                    
                    print(f"  Found {len(inspections)} inspections:")
                    for insp in inspections:
                            print(f"    - {insp['establishment_name']} ({insp['address']}): {insp['critical_violations']} crit / {insp['non_critical_violations']} non-crit")
                    
                    self.save_inspections(inspections, article['url'])
        finally:
            self.close_browser()

# Test with mock data if run directly
if __name__ == "__main__":
    # Mock data test
    mock_text_independence = """
    McDonald's, 123 Main St: 1 critical violations. 2 non-critical violations.
    Critical: Employee did not wash hands.
    
    Taco Bell, 456 Elm St: 0 critical violations. 0 non-critical violations.
    """
    
    scraper = ExaminerScraper(debug_mode=True)
    print("\n--- Testing Parse Logic ---")
    results = scraper.parse_inspections(mock_text_independence, "Independence")
    for r in results:
        print(r)
