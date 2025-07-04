from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import time

# 🔒 GLOBAL REUSABLE CLIENT
ddgs_client = DDGS()

def search_duckduckgo(query, max_results=5):
    """
    Search DuckDuckGo and return URLs
    """
    try:
        results = ddgs_client.text(query, max_results=max_results)
        return [result['href'] for result in results]
    except Exception as e:
        print(f"⚠️ Search error: {str(e)}")
        return []

def scrape_page(url, timeout=10):
    """
    Scrape content from a webpage
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
            element.decompose()

        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        text = main_content.get_text(separator='\n', strip=True)
        return ' '.join(text.split())

    except Exception as e:
        print(f"⚠️ Failed to scrape {url}: {str(e)}")
        return ""
