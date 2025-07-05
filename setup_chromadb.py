#!/usr/bin/env python3
"""
Setup script for ChromaDB cache system.
This script will help you set up ChromaDB and verify the installation.
"""

import subprocess
import sys
import os

def install_chromadb():
    """
    Install ChromaDB using pip
    """
    print("📦 Installing ChromaDB...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb>=0.4.0"])
        print("✅ ChromaDB installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install ChromaDB: {e}")
        return False

def test_chromadb():
    """
    Test if ChromaDB is working properly
    """
    print("🧪 Testing ChromaDB installation...")
    try:
        import chromadb
        print(f"✅ ChromaDB version: {chromadb.__version__}")
        
        # Test basic functionality
        client = chromadb.Client()
        collection = client.create_collection("test_collection")
        
        # Add a test item
        collection.add(
            ids=["test1"],
            embeddings=[[0.1, 0.2, 0.3]],
            documents=["test document"],
            metadatas=[{"test": "metadata"}]
        )
        
        # Query the test item
        results = collection.query(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=1
        )
        
        if results and results['documents']:
            print("✅ ChromaDB is working correctly!")
            return True
        else:
            print("❌ ChromaDB test failed - no results returned")
            return False
            
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False

def setup_cache_directory():
    """
    Create the cache directory for ChromaDB
    """
    cache_dir = "./chroma_db"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"📁 Created cache directory: {cache_dir}")
    else:
        print(f"📁 Cache directory already exists: {cache_dir}")

def verify_sentence_transformers():
    """
    Verify that sentence-transformers is installed
    """
    print("🔍 Checking sentence-transformers...")
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers version: {sentence_transformers.__version__}")
        return True
    except ImportError:
        print("❌ sentence-transformers not found!")
        print("Please install it with: pip install sentence-transformers")
        return False

def main():
    """
    Main setup function
    """
    print("🎯 ChromaDB Cache Setup")
    print("=" * 30)
    
    # Check if ChromaDB is already installed
    try:
        import chromadb
        print(f"✅ ChromaDB is already installed (version: {chromadb.__version__})")
        chromadb_installed = True
    except ImportError:
        print("📦 ChromaDB not found, installing...")
        chromadb_installed = install_chromadb()
    
    if not chromadb_installed:
        print("❌ ChromaDB installation failed. Please install manually:")
        print("   pip install chromadb>=0.4.0")
        return False
    
    # Verify sentence-transformers
    if not verify_sentence_transformers():
        return False
    
    # Test ChromaDB
    if not test_chromadb():
        return False
    
    # Setup cache directory
    setup_cache_directory()
    
    # Test our cache implementation
    print("🧪 Testing cache implementation...")
    try:
        from cache_chromadb import ChromaDBCache
        cache = ChromaDBCache()
        
        # Test add and find
        test_query = "test query for setup"
        test_summary = "This is a test summary"
        
        cache.add_to_cache(test_query, test_summary)
        result, similarity = cache.find_similar_query(test_query, threshold=0.5)
        
        if result and similarity:
            print(f"✅ Cache test successful! Similarity: {similarity:.2f}")
            
            # Get stats
            stats = cache.get_cache_stats()
            print(f"📊 Cache stats: {stats}")
            
            # Clean up test data
            cache.clear_cache()
            print("🧹 Cleaned up test data")
            
        else:
            print("❌ Cache test failed")
            return False
            
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run your Flask app: python app.py")
    print("2. If you have old cache data, run: python migrate_cache.py")
    print("3. Check cache stats at: http://localhost:5000/cache-stats")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)