import chromadb
from sentence_transformers import SentenceTransformer, util
import uuid
import os

class ChromaDBCache:
    def __init__(self, collection_name="query_cache", db_path="./chroma_db"):
        """
        Initialize ChromaDB cache
        
        Args:
            collection_name: Name of the ChromaDB collection
            db_path: Path to store ChromaDB files
        """
        # Create ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create or get collection with cosine similarity
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Load the same embedding model
        self.model = SentenceTransformer("embedding_model")
        
        print(f"ChromaDB Cache initialized with {self.collection.count()} cached queries")
    
    def find_similar_query(self, new_query, threshold=0.75):
        """
        Find similar query in cache
        
        Args:
            new_query: Query string to search for
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            tuple: (summary, similarity) if found, (None, None) if not found
        """
        try:
            # Generate embedding for new query
            new_embedding = self.model.encode([new_query])[0]
            
            # Search ChromaDB for similar queries
            results = self.collection.query(
                query_embeddings=[new_embedding.tolist()],
                n_results=1
            )
            
            # Check if we found results
            if results['documents'] and len(results['documents'][0]) > 0:
                # ChromaDB returns cosine distance, convert to similarity
                distance = results['distances'][0][0]
                similarity = 1 - distance
                
                print(f"🧪 Similarity with: \"{results['documents'][0][0]}\" = {similarity:.2f}")
                
                if similarity >= threshold:
                    summary = results['metadatas'][0][0]['summary']
                    return summary, similarity
            
            return None, None
            
        except Exception as e:
            print(f"Error in find_similar_query: {e}")
            return None, None
    
    def add_to_cache(self, query, summary):
        """
        Add query and summary to cache
        
        Args:
            query: Query string
            summary: Summary text to cache
        """
        try:
            # Generate embedding
            embedding = self.model.encode([query])[0]
            
            # Create unique ID
            query_id = str(uuid.uuid4())
            
            # Add to ChromaDB
            self.collection.add(
                ids=[query_id],
                embeddings=[embedding.tolist()],
                documents=[query],
                metadatas=[{"summary": summary}]
            )
            
            print(f"✅ Added to cache: \"{query[:50]}{'...' if len(query) > 50 else ''}\"")
            
        except Exception as e:
            print(f"Error adding to cache: {e}")
    
    def get_cache_stats(self):
        """
        Get cache statistics
        
        Returns:
            dict: Cache statistics
        """
        try:
            count = self.collection.count()
            return {
                "total_queries": count,
                "collection_name": self.collection.name,
                "database_path": "./chroma_db"
            }
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """
        Clear all cache entries
        """
        try:
            # Delete the collection
            self.client.delete_collection(self.collection.name)
            
            # Recreate the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection.name,
                metadata={"hnsw:space": "cosine"}
            )
            
            print("🗑️ Cache cleared successfully")
            
        except Exception as e:
            print(f"Error clearing cache: {e}")

# Create global cache instance
cache_db = ChromaDBCache()

# Wrapper functions to match the original API
def find_similar_query(new_query, threshold=0.75):
    """
    Find similar query in cache
    
    Args:
        new_query: Query string to search for
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        tuple: (summary, similarity) if found, (None, None) if not found
    """
    return cache_db.find_similar_query(new_query, threshold)

def add_to_cache(query, summary):
    """
    Add query and summary to cache
    
    Args:
        query: Query string
        summary: Summary text to cache
    """
    return cache_db.add_to_cache(query, summary)

def get_cache_stats():
    """
    Get cache statistics
    
    Returns:
        dict: Cache statistics
    """
    return cache_db.get_cache_stats()

def clear_cache():
    """
    Clear all cache entries
    """
    return cache_db.clear_cache()

def view_all_cache():
    """
    View all cached queries
    
    Returns:
        list: List of all cached queries with metadata
    """
    try:
        # Get all items from cache
        results = cache_db.collection.get()
        
        cache_items = []
        for i in range(len(results['ids'])):
            cache_items.append({
                'id': results['ids'][i],
                'query': results['documents'][i],
                'summary': results['metadatas'][i]['summary'][:100] + '...' if len(results['metadatas'][i]['summary']) > 100 else results['metadatas'][i]['summary'],
                'full_summary': results['metadatas'][i]['summary']
            })
        
        return cache_items
    except Exception as e:
        print(f"Error viewing cache: {e}")
        return []

def search_cache(search_term):
    """
    Search for specific queries in cache
    
    Args:
        search_term: Term to search for in queries
        
    Returns:
        list: Matching cache items
    """
    try:
        all_items = view_all_cache()
        matching_items = []
        
        for item in all_items:
            if search_term.lower() in item['query'].lower():
                matching_items.append(item)
        
        return matching_items
    except Exception as e:
        print(f"Error searching cache: {e}")
        return []

def delete_cache_item(query_id):
    """
    Delete a specific item from cache
    
    Args:
        query_id: ID of the query to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cache_db.collection.delete(ids=[query_id])
        print(f"🗑️ Deleted cache item: {query_id}")
        return True
    except Exception as e:
        print(f"Error deleting cache item: {e}")
        return False

def delete_cache_by_query(query_text):
    """
    Delete cache items by query text
    
    Args:
        query_text: Query text to search and delete
        
    Returns:
        int: Number of items deleted
    """
    try:
        matching_items = search_cache(query_text)
        deleted_count = 0
        
        for item in matching_items:
            if delete_cache_item(item['id']):
                deleted_count += 1
        
        print(f"🗑️ Deleted {deleted_count} cache items matching: {query_text}")
        return deleted_count
    except Exception as e:
        print(f"Error deleting cache items: {e}")
        return 0
