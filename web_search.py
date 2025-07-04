import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.parse
from typing import List, Dict, Optional

# Rotating User Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_random_headers():
    """Get randomized headers to avoid detection"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def search_google_scrape(query: str, max_results: int = 5) -> List[str]:
    """
    Scrape Google search results directly (backup method)
    """
    try:
        headers = get_random_headers()
        params = {
            'q': query,
            'num': max_results,
            'hl': 'en'
        }
        
        url = "https://www.google.com/search"
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result links
            links = []
            for g in soup.find_all('div', class_='g'):
                link = g.find('a')
                if link and link.get('href'):
                    href = link['href']
                    if href.startswith('/url?q='):
                        # Extract actual URL from Google redirect
                        actual_url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q')
                        if actual_url:
                            links.append(actual_url[0])
                    elif href.startswith('http'):
                        links.append(href)
                        
                if len(links) >= max_results:
                    break
                    
            print(f"✅ Google scrape found {len(links)} results")
            return links
        else:
            print(f"⚠️ Google search failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ Google scrape error: {str(e)}")
        return []

def search_bing_scrape(query: str, max_results: int = 5) -> List[str]:
    """
    Scrape Bing search results directly
    """
    try:
        headers = get_random_headers()
        params = {
            'q': query,
            'count': max_results
        }
        
        url = "https://www.bing.com/search"
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for result in soup.find_all('h2'):
                link = result.find('a')
                if link and link.get('href'):
                    href = link['href']
                    if href.startswith('http'):
                        links.append(href)
                        
                if len(links) >= max_results:
                    break
                    
            print(f"✅ Bing scrape found {len(links)} results")
            return links
        else:
            print(f"⚠️ Bing search failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ Bing scrape error: {str(e)}")
        return []

def search_duckduckgo_lite(query: str, max_results: int = 5) -> List[str]:
    """
    Use DuckDuckGo HTML interface (more reliable than API)
    """
    try:
        headers = get_random_headers()
        params = {
            'q': query,
            'kl': 'us-en'
        }
        
        url = "https://html.duckduckgo.com/html/"
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for result in soup.find_all('a', class_='result__url'):
                href = result.get('href')
                if href and href.startswith('http'):
                    links.append(href)
                    
                if len(links) >= max_results:
                    break
                    
            print(f"✅ DuckDuckGo HTML found {len(links)} results")
            return links
        else:
            print(f"⚠️ DuckDuckGo HTML failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ DuckDuckGo HTML error: {str(e)}")
        return []

def search_multi_engine(query: str, max_results: int = 5) -> List[str]:
    """
    Try multiple search engines in sequence until one works
    """
    print(f"🔍 Searching for: {query}")
    
    # List of search methods to try in order
    search_methods = [
        ("DuckDuckGo HTML", search_duckduckgo_lite),
        ("Bing Scrape", search_bing_scrape),
        ("Google Scrape", search_google_scrape),
    ]
    
    for method_name, search_func in search_methods:
        try:
            print(f"🔄 Trying {method_name}...")
            results = search_func(query, max_results)
            
            if results:
                print(f"✅ {method_name} successful! Found {len(results)} results")
                return results
            else:
                print(f"❌ {method_name} returned no results")
                
        except Exception as e:
            print(f"❌ {method_name} failed: {str(e)}")
            
        # Wait between attempts
        time.sleep(random.uniform(1, 3))
    
    print("❌ All search methods failed")
    return []

def scrape_page(url: str, timeout: int = 10) -> str:
    """
    Scrape content from a webpage with improved error handling
    """
    headers = get_random_headers()

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'header']):
            element.decompose()

        # Extract main content - try multiple selectors
        main_content = (
            soup.find('article') or 
            soup.find('main') or 
            soup.find('div', class_=lambda x: x and any(keyword in x.lower() for keyword in ['content', 'article', 'post', 'body'])) or
            soup.find('body')
        )
        
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

def search_and_scrape(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Combined function to search and scrape content from top results
    """
    urls = search_multi_engine(query, max_results)
    
    if not urls:
        print("❌ No search results found from any search engine")
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
        
        # Add delay between scraping requests
        if i < len(urls) - 1:
            time.sleep(random.uniform(2, 4))
    
    print(f"✅ Successfully scraped {len(results)} pages")
    return results

# Legacy function names for compatibility
def search_duckduckgo(query: str, max_results: int = 5, max_retries: int = 3) -> List[str]:
    """Legacy function - now uses multi-engine search"""
    return search_multi_engine(query, max_results)
