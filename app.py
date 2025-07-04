from flask import Flask, render_template, request, jsonify
from agent import classify_query
from cache import find_similar_query, add_to_cache
from web_search import search_duckduckgo, scrape_page
from summarizer import summarize_text
import time
import os

# Set environment variable for tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = Flask(__name__)

def web_process_query(query):
    """
    Exact replica of main.py logic for consistent quality results
    """
    results_log = []  # For tracking progress
    
    # Step 1: Validate query (same as main.py)
    if classify_query(query) == "invalid":
        raise ValueError("❌ Invalid query")
    
    # Step 2: Check cache (same as main.py)
    cached, similarity = find_similar_query(query)
    if cached:
        results_log.append(f"✅ Using cached result (similarity: {similarity:.2f})")
        return {
            "summary": cached,
            "is_cached": True,
            "similarity": float(similarity),
            "log": results_log
        }
    
    # Step 3: Search the web (same as main.py)
    results_log.append("🌐 Searching web...")
    urls = search_duckduckgo(query)
    if not urls:
        raise ValueError("⚠️ No search results found")
    
    # Step 4: Scrape top 5 pages (EXACTLY like main.py)
    results_log.append(f"📄 Found {len(urls)} search results")
    contents = []
    
    for i, url in enumerate(urls[:5], 1):  # Changed from 3 to 5 pages like main.py
        results_log.append(f"🔗 [{i}/5] Scraping: {url}")
        content = scrape_page(url)
        if content:
            contents.append(content[:5000])  # Limit size (same as main.py)
        time.sleep(1)  # Same delay as main.py
    
    if not contents:
        raise ValueError("⚠️ No content could be scraped")
    
    # Step 5: Summarize (same as main.py)
    combined = "\n\n".join(contents)
    results_log.append("✂️ Summarizing scraped content...")
    
    try:
        summary = summarize_text(combined)
    except Exception as e:
        raise ValueError(f"❌ Summarization failed: {e}")
    
    # Step 6: Cache and return result (same as main.py)
    add_to_cache(query, summary)
    results_log.append("✅ Summary generated and cached")
    
    return {
        "summary": summary,
        "is_cached": False,
        "pages_scraped": len(contents),
        "total_content_length": len(combined),
        "log": results_log
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Please enter a search query'}), 400
    
    try:
        result = web_process_query(query)
        return jsonify({
            'summary': result['summary'],
            'is_cached': result.get('is_cached', False),
            'similarity': result.get('similarity', 0),
            'pages_scraped': result.get('pages_scraped', 0),
            'total_content_length': result.get('total_content_length', 0),
            'processing_log': result.get('log', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)