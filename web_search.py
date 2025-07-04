import requests
from bs4 import BeautifulSoup
import time
import random
import urllib.parse
import re
from typing import List, Dict, Optional

# Rotating User Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Quality domains - prioritize these sources
QUALITY_DOMAINS = [
    'wikipedia.org', 'britannica.com', 'nationalgeographic.com', 'nature.com', 
    'sciencedirect.com', 'smithsonianmag.com', 'scientificamerican.com',
    'bbc.com', 'reuters.com', 'ap.org', 'cnn.com', 'npr.org',
    'tripadvisor.com', 'lonelyplanet.com', 'booking.com', 'expedia.com',
    'airbnb.com', 'hotels.com', 'agoda.com', 'makemytrip.com',
    'edu', 'gov', 'org', 'com'
]

# Low quality domains to avoid
BAD_DOMAINS = [
    'pinterest.com', 'yahoo.answers', 'wiki.answers.com', 
    'chacha.com', 'blurtit.com', 'weegy.com'
]

def enhance_query(query: str) -> str:
    """
    Enhance search queries for better results
    """
    query = query.lower().strip()
    
    # Query patterns and their enhancements
    enhancements = {
        # Animal queries
        r'(biggest|largest|biggest) animal': 'largest animal in the world blue whale facts',
        r'(smallest|tiniest) animal': 'smallest animal in the world facts',
        r'what is.*animal': query + ' facts information',
        
        # Science queries  
        r'how does.*work': query + ' explanation science',
        r'what is.*made of': query + ' composition materials',
        r'why is.*': query + ' explanation reason',
        
        # History queries
        r'when did.*happen': query + ' historical facts',
        r'who was.*': query + ' biography historical facts',
        
        # Geography queries
        r'where is.*': query + ' location geography facts',
        r'what is.*capital': query + ' geography',
        
        # General enhancement
        r'.*': query + ' facts information'
    }
    
    for pattern, enhancement in enhancements.items():
        if re.match(pattern, query):
            enhanced = enhancement
            print(f"🔍 Enhanced query: '{query}' → '{enhanced}'")
            return enhanced
    
    return query + ' facts information'

def filter_quality_urls(urls: List[str]) -> List[str]:
    """
    Filter and sort URLs by quality
    """
    def get_domain_score(url: str) -> int:
        """Score URLs based on domain quality"""
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            
            # Check for quality domains
            for quality_domain in QUALITY_DOMAINS:
                if quality_domain in domain:
                    return 100  # High priority
            
            # Check for bad domains
            for bad_domain in BAD_DOMAINS:
                if bad_domain in domain:
                    return 0  # Skip these
            
            # Moderate quality for others
            return 50
            
        except:
            return 25

    # Filter out bad domains and sort by quality
    filtered_urls = []
    for url in urls:
        score = get_domain_score(url)
        if score > 0:  # Skip score 0 (bad domains)
            filtered_urls.append((url, score))
    
    # Sort by score (highest first) and return URLs
    filtered_urls.sort(key=lambda x: x[1], reverse=True)
    result = [url for url, score in filtered_urls]
    
    print(f"✅ Filtered {len(urls)} → {len(result)} quality URLs")
    return result

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

def search_google_scrape(query: str, max_results: int = 10) -> List[str]:
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
        print(f"🌐 Requesting Google: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"📡 Google response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result links with multiple selectors
            links = []
            
            # Try multiple Google result selectors
            selectors = [
                'div.g a',  # Standard results
                'div[data-ved] a',  # Alternative results
                'h3 a',  # Header links
                'a[href^="/url?q="]',  # URL-encoded links
                'a[href^="http"]'  # Direct HTTP links
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    href = element.get('href')
                    if href:
                        if href.startswith('/url?q='):
                            # Extract actual URL from Google redirect
                            try:
                                actual_url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q')
                                if actual_url:
                                    clean_url = actual_url[0]
                                    if clean_url.startswith('http') and clean_url not in links:
                                        links.append(clean_url)
                            except:
                                continue
                        elif href.startswith('http') and href not in links:
                            links.append(href)
                            
                    if len(links) >= max_results:
                        break
                
                if links:  # If we found links with this selector, use them
                    break
                    
            print(f"✅ Google scrape found {len(links)} raw results")
            
            # Debug: Print first few URLs
            for i, link in enumerate(links[:3]):
                print(f"  {i+1}. {link}")
            
            return filter_quality_urls(links)
        else:
            print(f"⚠️ Google search failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ Google scrape error: {str(e)}")
        return []

def search_bing_scrape(query: str, max_results: int = 10) -> List[str]:
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
            return filter_quality_urls(links)
        else:
            print(f"⚠️ Bing search failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ Bing scrape error: {str(e)}")
        return []

def search_duckduckgo_lite(query: str, max_results: int = 10) -> List[str]:
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
        print(f"🌐 Requesting DuckDuckGo: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"📡 DuckDuckGo response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            
            # Try multiple DuckDuckGo selectors
            selectors = [
                'a.result__url',  # Standard results
                'a[class*="result"]',  # Alternative result links
                '.result h2 a',  # Header links in results
                '.results a[href^="http"]'  # Direct HTTP links in results
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                print(f"🔍 Found {len(elements)} elements with selector: {selector}")
                
                for element in elements:
                    href = element.get('href')
                    if href and href.startswith('http') and href not in links:
                        links.append(href)
                        
                    if len(links) >= max_results:
                        break
                
                if links:  # If we found links with this selector, use them
                    break
            
            # If no links found, try a more general approach
            if not links:
                print("🔍 Trying general link extraction...")
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    if href.startswith('http') and 'duckduckgo.com' not in href:
                        links.append(href)
                        if len(links) >= max_results:
                            break
                            
            print(f"✅ DuckDuckGo HTML found {len(links)} raw results")
            
            # Debug: Print first few URLs
            for i, link in enumerate(links[:3]):
                print(f"  {i+1}. {link}")
            
            return filter_quality_urls(links)
        else:
            print(f"⚠️ DuckDuckGo HTML failed with status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"⚠️ DuckDuckGo HTML error: {str(e)}")
        return []

def search_multi_engine(query: str, max_results: int = 5) -> List[str]:
    """
    Try multiple search engines with enhanced queries (DuckDuckGo + Google only)
    """
    enhanced_query = enhance_query(query)
    print(f"🔍 Searching for: {enhanced_query}")
    
    # List of search methods to try in order (skipping Bing for better quality)
    search_methods = [
        ("DuckDuckGo HTML", search_duckduckgo_lite),
        ("Google Scrape", search_google_scrape),
    ]
    
    for method_name, search_func in search_methods:
        try:
            print(f"🔄 Trying {method_name}...")
            results = search_func(enhanced_query, max_results * 2)  # Get more results to filter
            
            if results:
                # Take top results after filtering
                final_results = results[:max_results]
                print(f"✅ {method_name} successful! Found {len(final_results)} quality results")
                return final_results
            else:
                print(f"❌ {method_name} returned no quality results")
                
        except Exception as e:
            print(f"❌ {method_name} failed: {str(e)}")
            
        # Wait between attempts
        time.sleep(random.uniform(1, 3))
    
    print("❌ All search methods failed")
    return []

def extract_relevant_content(soup: BeautifulSoup, query: str) -> str:
    """
    Extract the most relevant content based on query context
    """
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript', 'header', 'aside']):
        element.decompose()

    # Try different content extraction strategies
    content_selectors = [
        'article',
        'main', 
        '[role="main"]',
        '.content',
        '.article-content',
        '.post-content',
        '.entry-content',
        '#content',
        '.main-content'
    ]
    
    extracted_content = ""
    
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            # Get paragraphs from this section
            paragraphs = content_elem.find_all('p')
            if len(paragraphs) >= 2:  # Ensure substantial content
                extracted_content = content_elem.get_text(separator=' ', strip=True)
                break
    
    # Fallback to body if no specific content area found
    if not extracted_content:
        body = soup.find('body')
        if body:
            extracted_content = body.get_text(separator=' ', strip=True)
    
    # Clean up the text
    if extracted_content:
        # Remove extra whitespace
        extracted_content = ' '.join(extracted_content.split())
        
        # Try to find the most relevant paragraphs
        sentences = extracted_content.split('.')
        relevant_sentences = []
        
        query_words = set(query.lower().split())
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Ignore very short sentences
                sentence_words = set(sentence.lower().split())
                # Check if sentence contains query-related words
                if query_words.intersection(sentence_words) or len(relevant_sentences) < 3:
                    relevant_sentences.append(sentence)
                    
        return '. '.join(relevant_sentences[:10])  # Take first 10 relevant sentences
    
    return ""

def scrape_page(url: str, timeout: int = 15) -> str:
    """
    Scrape content from a webpage with improved content extraction
    """
    headers = get_random_headers()

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract relevant content
        content = extract_relevant_content(soup, "")
        
        if content and len(content) > 100:  # Ensure we got substantial content
            return content
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
        if content and len(content) > 50:  # Ensure quality content
            results.append({
                'url': url,
                'content': content[:3000] + '...' if len(content) > 3000 else content
            })
        else:
            print(f"⚠️ Skipped {url} - insufficient content")
        
        # Add delay between scraping requests
        if i < len(urls) - 1:
            time.sleep(random.uniform(2, 4))
    
    print(f"✅ Successfully scraped {len(results)} quality pages")
    return results

# Legacy function names for compatibility
def search_duckduckgo(query: str, max_results: int = 5, max_retries: int = 3) -> List[str]:
    """Legacy function - now uses enhanced multi-engine search"""
    return search_multi_engine(query, max_results)
