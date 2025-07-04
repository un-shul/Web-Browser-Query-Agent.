import os
import time
from web_search import search_duckduckgo, scrape_page
from cache import find_similar_query, add_to_cache
from agent import classify_query
from summarizer import summarize_text

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main():
    while True:
        query = input("\nEnter your query (or 'exit'): ").strip()
        if query.lower() == "exit":
            break

        # Step 1: Validate query
        if classify_query(query) == "invalid":
            print("❌ Invalid query")
            continue

        # Step 2: Check cache
        cached, similarity = find_similar_query(query)
        if cached:
            print(f"✅ Using cached result (similarity: {similarity:.2f})")
            print("\n📄 Summary:\n" + cached)
            continue

        # Step 3: Search the web
        print("🌐 Searching web...")
        urls = search_duckduckgo(query)
        if not urls:
            print("⚠️ No search results found")
            continue

        # Step 4: Scrape top 5 pages
        contents = []
        for i, url in enumerate(urls[:5], 1):
            print(f"\n🔗 [{i}/5] Scraping: {url}")
            content = scrape_page(url)
            if content:
                contents.append(content[:5000])  # Limit size
            time.sleep(1)

        if not contents:
            print("⚠️ No content could be scraped")
            continue

        # Step 5: Summarize
        combined = "\n\n".join(contents)
        print("\n✂️ Summarizing scraped content...")
        try:
            summary = summarize_text(combined, query)
        except Exception as e:
            print(f"❌ Summarization failed: {e}")
            continue

        # Step 6: Cache and show result
        add_to_cache(query, summary)
        print("\n📄 Summary:\n" + summary)

if __name__ == "__main__":
    main()
