from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.parse
import re
from typing import List, Dict

# 🔒 GLOBAL REUSABLE CLIENT
ddgs_client = DDGS()

# Rate limiting variables
_last_search_time = 0
_min_search_interval = 2.0  # Minimum seconds between searches

# Simple user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
]

# Content filtering patterns for better quality extraction
AD_PATTERNS = [
    r'advertisement', r'sponsored', r'promo', r'click here', r'buy now', r'shop now',
    r'subscribe', r'newsletter', r'follow us', r'share this', r'like us on',
    r'cookie policy', r'privacy policy', r'terms of service', r'accept cookies',
    r'log in', r'sign up', r'register', r'create account', r'login', r'signin',
    r'download app', r'get the app', r'install', r'app store', r'google play'
]

UNWANTED_SELECTORS = [
    # Navigation and UI elements
    'nav', 'header', 'footer', 'aside', 'sidebar',
    # Ads and promotional content
    '.ad', '.ads', '.advertisement', '.sponsored', '.promo', '.banner',
    '[class*="ad-"]', '[id*="ad-"]', '[class*="ads-"]', '[id*="ads-"]',
    # Social and sharing
    '.social', '.share', '.sharing', '.follow', '.subscribe',
    # Comments and user-generated content
    '.comments', '.comment', '.reviews', '.review', '.testimonial',
    # Forms and login
    '.login', '.signup', '.register', '.newsletter', '.subscribe-form',
    # Cookie and privacy notices
    '.cookie', '.privacy', '.gdpr', '.consent',
    # Navigation elements
    '.breadcrumb', '.pagination', '.tags', '.categories',
    # Other unwanted elements
    '.popup', '.modal', '.overlay', '.widget', '.related', '.recommended'
]

def get_headers():
    """Get simple headers"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

def search_duckduckgo_simple(query: str, max_results: int = 5) -> List[str]:
    """
    Simple DuckDuckGo search - just get results without filtering
    """
    try:
        search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        print(f"🌐 Searching DuckDuckGo...")
        
        response = requests.get(search_url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('a', class_='result__url', href=True)
        
        urls = []
        for link in results[:max_results]:
            url = link['href']
            # Extract actual URL from DuckDuckGo redirect
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'uddg' in query_params:
                actual_url = query_params['uddg'][0]
                urls.append(actual_url)
            elif url.startswith('http'):
                urls.append(url)
                
        print(f"✅ Found {len(urls)} results")
        return urls
        
    except Exception as e:
        print(f"⚠️ DuckDuckGo error: {str(e)}")
        return []

def search_google_simple(query: str, max_results: int = 5) -> List[str]:
    """
    Simple Google search fallback
    """
    try:
        params = {
            'q': query,
            'num': max_results,
            'hl': 'en'
        }
        
        url = "https://www.google.com/search"
        print(f"🌐 Searching Google as fallback...")
        
        response = requests.get(url, params=params, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        urls = []
        # Look for any links that start with http
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/url?q='):
                # Extract from Google redirect
                try:
                    actual_url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q', [None])[0]
                    if actual_url and actual_url.startswith('http') and 'google.com' not in actual_url:
                        urls.append(actual_url)
                except:
                    continue
            elif href.startswith('http') and 'google.com' not in href:
                urls.append(href)
                
            if len(urls) >= max_results:
                break
                
        print(f"✅ Found {len(urls)} results")
        return urls
        
    except Exception as e:
        print(f"⚠️ Google error: {str(e)}")
        return []

def search_duckduckgo(query: str, max_results: int = 5, max_retries: int = 3) -> List[str]:
    """
    Main search function - compatible with main.py and app.py
    """
    print(f"🔍 Searching for: {query}")
    
    # Try DuckDuckGo first
    urls = search_duckduckgo_simple(query, max_results)
    
    # If DuckDuckGo fails, try Google
    if not urls:
        print("🔄 Trying Google...")
        urls = search_google_simple(query, max_results)
    
    return urls

def filter_content_quality(text: str) -> str:
    """
    Filter out low-quality content using patterns and heuristics
    """
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip lines that are too short (likely navigation or labels)
        if len(line) < 20:
            continue
            
        # Skip lines with high ratio of special characters
        if len(re.sub(r'[a-zA-Z\s]', '', line)) / len(line) > 0.3:
            continue
            
        # Skip lines matching ad patterns
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in AD_PATTERNS):
            continue
            
        # Skip lines that are mostly uppercase (likely headings/navigation)
        if len(line) > 10 and sum(1 for c in line if c.isupper()) / len(line) > 0.5:
            continue
            
        # Skip lines with email patterns
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line):
            continue
            
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def extract_main_content(soup: BeautifulSoup) -> str:
    """
    Extract the main content from a webpage using multiple strategies
    """
    # Remove unwanted elements - expanded list
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        element.decompose()
    
    # Remove elements by selector
    for selector in UNWANTED_SELECTORS:
        for element in soup.select(selector):
            element.decompose()
    
    # Remove elements with specific attributes indicating ads/unwanted content
    for element in soup.find_all(attrs={'class': re.compile(r'(ad|ads|advertisement|sponsored|promo)', re.I)}):
        element.decompose()
    
    for element in soup.find_all(attrs={'id': re.compile(r'(ad|ads|advertisement|sponsored|promo)', re.I)}):
        element.decompose()
    
    # Try to find main content using semantic HTML5 tags
    content_candidates = [
        soup.find('article'),
        soup.find('main'),
        soup.find('[role="main"]'),
        soup.find('div', class_=re.compile(r'(content|article|post|story)', re.I)),
        soup.find('div', id=re.compile(r'(content|article|post|story)', re.I))
    ]
    
    # Find the best content candidate
    best_content = None
    max_text_length = 0
    
    for candidate in content_candidates:
        if candidate:
            text = candidate.get_text(separator=' ', strip=True)
            if len(text) > max_text_length:
                max_text_length = len(text)
                best_content = candidate
    
    # Fallback to body if no specific content area found
    if not best_content:
        best_content = soup.find('body')
    
    if best_content:
        # Extract text and clean it
        text = best_content.get_text(separator='\n', strip=True)
        # Filter out low-quality content
        text = filter_content_quality(text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text
    
    return ""

def scrape_page(url: str, timeout: int = 10) -> str:
    """
    Improved page scraping with better content filtering
    """
    try:
        response = requests.get(url, headers=get_headers(), timeout=timeout)
        
        if response.status_code != 200:
            return ""
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Use improved content extraction
        text = extract_main_content(soup)
        
        # Additional quality check - content should be substantial
        if len(text) < 100:
            print(f"⚠️ Content too short from {url}, skipping")
            return ""
        
        # Return first 5000 characters (same as your original)
        return text[:5000] if text else ""
        
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {str(e)}")
        return ""

def search_and_scrape(query: str, max_results: int = 3, max_retries: int = 3) -> List[Dict[str, str]]:
    """
    Combined search and scrape - compatible with app.py
    """
    urls = search_duckduckgo(query, max_results)
    
    if not urls:
        print("❌ No URLs found")
        return []
    
    results = []
    for i, url in enumerate(urls):
        print(f"📄 Scraping result {i+1}/{len(urls)}: {url}")
        content = scrape_page(url)
        if content and len(content) > 100:  # Only keep substantial content
            results.append({
                'url': url,
                'content': content[:2000] + '...' if len(content) > 2000 else content
            })
        
        # Small delay between requests
        if i < len(urls) - 1:
            time.sleep(1)
    
    print(f"✅ Successfully scraped {len(results)} pages")
    return results
