import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.parse
from typing import List, Dict

# Simple user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
        print(f"🌐 Searching DuckDuckGo: {search_url}")
        
        response = requests.get(search_url, headers=get_headers(), timeout=15)
        print(f"📡 Response status: {response.status_code}")
        
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
                print(f"  Found: {actual_url}")
            elif url.startswith('http'):
                urls.append(url)
                print(f"  Found: {url}")
                
        print(f"✅ DuckDuckGo found {len(urls)} results")
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
        print(f"🌐 Searching Google as fallback")
        
        response = requests.get(url, params=params, headers=get_headers(), timeout=15)
        print(f"📡 Response status: {response.status_code}")
        
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
                        print(f"  Found: {actual_url}")
                except:
                    continue
            elif href.startswith('http') and 'google.com' not in href:
                urls.append(href)
                print(f"  Found: {href}")
                
            if len(urls) >= max_results:
                break
                
        print(f"✅ Google found {len(urls)} results")
        return urls
        
    except Exception as e:
        print(f"⚠️ Google error: {str(e)}")
        return []

def search_web(query: str, max_results: int = 5) -> List[str]:
    """
    Search web - try DuckDuckGo first, then Google
    """
    print(f"🔍 Searching for: {query}")
    
    # Try DuckDuckGo first
    urls = search_duckduckgo_simple(query, max_results)
    
    # If DuckDuckGo fails, try Google
    if not urls:
        print("🔄 DuckDuckGo failed, trying Google...")
        urls = search_google_simple(query, max_results)
    
    return urls

def scrape_page(url: str) -> str:
    """
    Simple page scraping
    """
    try:
        print(f"📄 Scraping: {url}")
        response = requests.get(url, headers=get_headers(), timeout=15)
        
        if response.status_code != 200:
            return ""
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
            element.decompose()
        
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up text
        text = ' '.join(text.split())
        
        # Return first 3000 characters
        return text[:3000] if text else ""
        
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {str(e)}")
        return ""

def search_and_scrape(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search and scrape - simple approach
    """
    urls = search_web(query, max_results)
    
    if not urls:
        print("❌ No URLs found")
        return []
    
    results = []
    for i, url in enumerate(urls):
        content = scrape_page(url)
        if content and len(content) > 100:  # Only keep substantial content
            results.append({
                'url': url,
                'content': content
            })
        
        # Small delay between requests
        if i < len(urls) - 1:
            time.sleep(1)
    
    print(f"✅ Successfully scraped {len(results)} pages")
    return results

# Legacy function names for compatibility
def search_duckduckgo(query: str, max_results: int = 5, max_retries: int = 3) -> List[str]:
    """Legacy function - simplified"""
    return search_web(query, max_results)

def scrape_page_legacy(url: str, timeout: int = 15) -> str:
    """Legacy function - simplified"""
    return scrape_page(url)
