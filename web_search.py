from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List, Optional

# 🔒 GLOBAL REUSABLE CLIENT
ddgs_client = DDGS()

# Rate limiting variables
_last_search_time = 0
_min_search_interval = 2.0  # Minimum seconds between searches

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

def scrape_page(url: str, timeout: int = 10) -> str:
    """
    Scrape content from a webpage with improved error handling
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
            element.decompose()

        # Extract main content
        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
            return ' '.join(text.split())
        else:
            return ""

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
