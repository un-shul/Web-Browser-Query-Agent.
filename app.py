from flask import Flask, render_template, request, jsonify, Response
from agent import classify_query
from cache_chromadb import find_similar_query, add_to_cache, get_cache_stats
from web_search import search_duckduckgo, scrape_page
from summarizer import summarize_text
import time
import os
import json

# Set environment variable for tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = Flask(__name__)

def web_process_query_with_progress(query):
    """
    Process query with real-time progress updates
    """
    def generate_progress():
        try:
            # Step 1: Validate query
            yield f"data: {json.dumps({'stage': 'validating', 'message': 'Validating your query...', 'progress': 5})}\n\n"
            
            if classify_query(query) == "invalid":
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Invalid query. Please try a different search term.', 'progress': 0})}\n\n"
                return
            
            # Step 2: Check cache
            yield f"data: {json.dumps({'stage': 'cache', 'message': 'Checking cache...', 'progress': 10})}\n\n"
            
            cached, similarity = find_similar_query(query)
            if cached:
                yield f"data: {json.dumps({'stage': 'complete', 'message': 'Found cached result!', 'progress': 100, 'summary': cached, 'is_cached': True, 'similarity': float(similarity)})}\n\n"
                return
            
            # Step 3: Search the web
            yield f"data: {json.dumps({'stage': 'searching', 'message': 'Searching DuckDuckGo...', 'progress': 15})}\n\n"
            
            urls = search_duckduckgo(query)
            if not urls:
                yield f"data: {json.dumps({'stage': 'error', 'message': 'No search results found. Please try a different query.', 'progress': 0})}\n\n"
                return
            
            yield f"data: {json.dumps({'stage': 'found', 'message': f'Found {len(urls)} results', 'progress': 25})}\n\n"
            
            # Step 4: Scrape pages with progress
            contents = []
            total_pages = min(len(urls), 5)
            
            for i, url in enumerate(urls[:5], 1):
                progress = 25 + (i * 10)  # 25% to 75%
                yield f"data: {json.dumps({'stage': 'scraping', 'message': f'Scraping page {i}/{total_pages}', 'progress': progress})}\n\n"
                
                content = scrape_page(url)
                if content:
                    contents.append(content[:5000])
                time.sleep(1)
            
            if not contents:
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Could not extract content from any pages. Please try again.', 'progress': 0})}\n\n"
                return
            
            # Step 5: Summarize
            yield f"data: {json.dumps({'stage': 'summarizing', 'message': 'Summarizing content...', 'progress': 80})}\n\n"
            
            combined = "\n\n".join(contents)
            summary = summarize_text(combined, query)
            
            # Step 6: Cache and return
            yield f"data: {json.dumps({'stage': 'caching', 'message': 'Saving result...', 'progress': 95})}\n\n"
            add_to_cache(query, summary)
            
            # Complete
            yield f"data: {json.dumps({'stage': 'complete', 'message': 'Summary ready!', 'progress': 100, 'summary': summary, 'is_cached': False, 'pages_scraped': len(contents), 'total_content_length': len(combined)})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'message': f'An error occurred: {str(e)}', 'progress': 0})}\n\n"
    
    return Response(generate_progress(), mimetype='text/event-stream')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search_progress', methods=['GET'])
def search_progress():
    query = request.args.get('query', '').strip()
    if not query:
        return Response(
            f"data: {json.dumps({'stage': 'error', 'message': 'Please enter a search query', 'progress': 0})}\n\n",
            mimetype='text/event-stream'
        )
    
    return web_process_query_with_progress(query)

@app.route('/search', methods=['POST'])
def search():
    """Fallback endpoint for non-SSE requests"""
    query = request.form.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Please enter a search query'}), 400
    
    # Simple validation
    if classify_query(query) == "invalid":
        return jsonify({'error': 'Invalid query. Please try a different search term.'}), 400
    
    try:
        # Check cache
        cached, similarity = find_similar_query(query)
        if cached:
            return jsonify({
                'summary': cached,
                'is_cached': True,
                'similarity': float(similarity)
            })
        
        # Search and process
        urls = search_duckduckgo(query)
        if not urls:
            return jsonify({'error': 'No search results found. Please try a different query.'}), 400
        
        # Scrape pages
        contents = []
        for url in urls[:5]:
            content = scrape_page(url)
            if content:
                contents.append(content[:5000])
            time.sleep(1)
        
        if not contents:
            return jsonify({'error': 'Could not extract content from any pages. Please try again.'}), 400
        
        # Summarize
        combined = "\n\n".join(contents)
        summary = summarize_text(combined, query)
        
        # Cache result
        add_to_cache(query, summary)
        
        return jsonify({
            'summary': summary,
            'is_cached': False,
            'pages_scraped': len(contents),
            'total_content_length': len(combined)
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    
@app.route('/cache-stats')
def cache_stats():
    """Get cache statistics"""
    stats = get_cache_stats()
    return jsonify(stats)

@app.route('/cache-view')
def cache_view():
    """View all cached queries"""
    from cache_chromadb import view_all_cache
    cache_items = view_all_cache()
    return jsonify({
        'total_items': len(cache_items),
        'items': cache_items
    })

@app.route('/cache-search')
def cache_search():
    """Search cached queries"""
    from cache_chromadb import search_cache
    search_term = request.args.get('q', '')
    if not search_term:
        return jsonify({'error': 'Please provide search term with ?q=your_term'})
    
    results = search_cache(search_term)
    return jsonify({
        'search_term': search_term,
        'found_items': len(results),
        'items': results
    })

@app.route('/cache-delete-item', methods=['POST'])
def cache_delete_item():
    """Delete a specific cache item"""
    from cache_chromadb import delete_cache_item
    data = request.get_json()
    
    if not data or 'id' not in data:
        return jsonify({'error': 'Please provide item ID'}), 400
    
    success = delete_cache_item(data['id'])
    if success:
        return jsonify({'message': 'Item deleted successfully'})
    else:
        return jsonify({'error': 'Failed to delete item'}), 500

@app.route('/cache-delete-query', methods=['POST'])
def cache_delete_query():
    """Delete cache items by query text"""
    from cache_chromadb import delete_cache_by_query
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Please provide query text'}), 400
    
    deleted_count = delete_cache_by_query(data['query'])
    return jsonify({
        'message': f'Deleted {deleted_count} items',
        'deleted_count': deleted_count
    })

@app.route('/cache-clear', methods=['POST'])
def cache_clear():
    """Clear entire cache"""
    from cache_chromadb import clear_cache
    try:
        clear_cache()
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)