import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.parse
import re
from typing import List, Dict

# Simple user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
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

def scrape_page(url: str, timeout: int = 10) -> str:
    """
    Improved scraping that removes sidebars, trending topics, and news widgets
    """
    try:
        response = requests.get(url, headers=get_headers(), timeout=timeout)
        
        if response.status_code != 200:
            return ""
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts, styles, and obvious junk
        for element in soup(['script', 'style', 'iframe', 'noscript']):
            element.decompose()
        
        # Remove sidebars, navigation, and common junk areas
        junk_selectors = [
            'nav', 'header', 'footer', 'aside', 
            '.sidebar', '.nav', '.navigation', '.menu',
            '.trending', '.popular', '.related', '.recommended',
            '.widgets', '.widget', '.ads', '.advertisement',
            '.social', '.share', '.follow', '.subscribe',
            '.comments', '.comment-section'
        ]
        
        for selector in junk_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Remove elements by common junk patterns in class/id names
        for element in soup.find_all(attrs={'class': re.compile(r'sidebar|trending|popular|widget|ad|advertisement|social|share|comment|related|recommended', re.I)}):
            element.decompose()
        
        for element in soup.find_all(attrs={'id': re.compile(r'sidebar|trending|popular|widget|ad|advertisement|social|share|comment|related|recommended', re.I)}):
            element.decompose()
        
        # Try to get main content - prioritize article content
        content_candidates = [
            soup.find('article'),
            soup.find('main'), 
            soup.find('[role="main"]'),
            soup.find('.content'),
            soup.find('#content'),
            soup.find('.article'),
            soup.find('#article'),
            soup.find('body')
        ]
        
        main_content = None
        for candidate in content_candidates:
            if candidate:
                main_content = candidate
                break
        
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            # Clean up text
            text = ' '.join(text.split())
            return text[:5000] if text else ""
        
        return ""
        
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