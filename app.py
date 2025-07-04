from flask import Flask, render_template, request, jsonify
from agent import classify_query
from cache import find_similar_query, add_to_cache
from web_search import search_duckduckgo, scrape_page
from summarizer import summarize_text
import time

app = Flask(__name__)

def web_process_query(query):
    """Adapted version of your CLI logic for web"""
    # 1. Validate query
    if classify_query(query) == "invalid":
        raise ValueError("Invalid query - please try a different search")
    
    # 2. Check cache
    cached, similarity = find_similar_query(query)
    if cached:
        return {
            "summary": cached,
            "is_cached": True,
            "similarity": float(similarity)
        }
    
    # 3. Search web (limit to 3 pages for faster response)
    urls = search_duckduckgo(query)
    if not urls:
        raise ValueError("No results found - try a different query")
    
    # 4. Scrape pages
    contents = []
    for url in urls[:3]:
        content = scrape_page(url)
        if content:
            contents.append(content[:5000])
        time.sleep(1)
    
    if not contents:
        raise ValueError("Couldn't extract content - please try again")
    
    # 5. Summarize
    summary = summarize_text("\n\n".join(contents))
    
    # 6. Cache result
    add_to_cache(query, summary)
    
    return {
        "summary": summary,
        "is_cached": False
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
            'similarity': result.get('similarity', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)