from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from typing import List, Optional

# 🔒 GLOBAL REUSABLE CLIENT
ddgs_client = DDGS()

# Rate limiting variables
_last_search_time = 0
_min_search_interval = 2.0  # Minimum seconds between searches

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

def search_duckduckgo(query: str, max_results: int = 5, max_retries: int = 3) -> List[str]:
    """
    Search DuckDuckGo and return URLs with proper rate limiting and retry logic
    """
    global _last_search_time
    
    # Implement rate limiting - wait if needed
    current_time = time.time()
    time_since_last = current_time - _last_search_time
    if time_since_last < _min_search_interval:
        sleep_time = _min_search_interval - time_since_last
        print(f"⏳ Rate limiting: waiting {sleep_time:.1f}s...")
        time.sleep(sleep_time)
    
    for attempt in range(max_retries):
        try:
            _last_search_time = time.time()
            results = ddgs_client.text(query, max_results=max_results)
            return [result['href'] for result in results]
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if 'ratelimit' in error_str or '202' in error_str:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    print(f"⚠️ Rate limited. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    
                    # Recreate client to reset any connection state
                    global ddgs_client
                    ddgs_client = DDGS()
                    continue
                else:
                    print(f"⚠️ Max retries reached. Rate limit error: {str(e)}")
                    return []
            else:
                print(f"⚠️ Search error: {str(e)}")
                return []
    
    return []

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
    # Remove unwanted elements
    for element in soup(['script', 'style', 'noscript', 'iframe']):
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
    Scrape content from a webpage with improved content filtering
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        content = extract_main_content(soup)
        
        # Additional quality check - content should be substantial
        if len(content) < 100:
            print(f"⚠️ Content too short from {url}, skipping")
            return ""
            
        return content

    except requests.exceptions.Timeout:
        print(f"⚠️ Timeout scraping {url}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Request error scraping {url}: {str(e)}")
        return ""
    except Exception as e:
        print(f"⚠️ Failed to scrape {url}: {str(e)}")
        return ""

def search_and_scrape(query: str, max_results: int = 3, max_retries: int = 3) -> List[dict]:
    """
    Combined function to search and scrape content from top results
    """
    print(f"🔍 Searching for: {query}")
    urls = search_duckduckgo(query, max_results, max_retries)
    
    if not urls:
        print("❌ No search results found")
        return []
    
    results = []
    for i, url in enumerate(urls):
        print(f"📄 Scraping result {i+1}/{len(urls)}: {url}")
        content = scrape_page(url)
        if content:
            results.append({
                'url': url,
                'content': content[:2000] + '...' if len(content) > 2000 else content
            })
        
        # Add small delay between scraping requests
        if i < len(urls) - 1:
            time.sleep(1)
    
    return results
