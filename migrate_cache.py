#!/usr/bin/env python3
"""
Migration script to move data from old pickle cache to new ChromaDB cache.
Run this script ONCE after setting up ChromaDB to migrate your existing cache data.
"""

import os
import pickle
from cache_chromadb import ChromaDBCache

# Configuration
OLD_CACHE_FILE = "query_cache.pkl"
BACKUP_CACHE_FILE = "query_cache_backup.pkl"

def migrate_cache():
    """
    Migrate data from old pickle cache to new ChromaDB cache
    """
    print("🔄 Starting cache migration...")
    
    # Check if old cache file exists
    if not os.path.exists(OLD_CACHE_FILE):
        print(f"❌ Old cache file '{OLD_CACHE_FILE}' not found.")
        print("No migration needed - starting fresh with ChromaDB!")
        return
    
    try:
        # Load old cache
        print(f"📖 Loading old cache from '{OLD_CACHE_FILE}'...")
        with open(OLD_CACHE_FILE, "rb") as f:
            old_cache = pickle.load(f)
        
        print(f"📊 Found {len(old_cache)} items in old cache")
        
        # Create backup
        print(f"💾 Creating backup at '{BACKUP_CACHE_FILE}'...")
        with open(BACKUP_CACHE_FILE, "wb") as f:
            pickle.dump(old_cache, f)
        
        # Initialize new ChromaDB cache
        print("🔧 Initializing ChromaDB cache...")
        chroma_cache = ChromaDBCache()
        
        # Migrate data
        print("🚀 Migrating data...")
        migrated_count = 0
        failed_count = 0
        
        for i, item in enumerate(old_cache):
            try:
                # Validate item structure
                if not isinstance(item, dict) or 'query' not in item or 'summary' not in item:
                    print(f"⚠️  Skipping invalid item {i}: {item}")
                    failed_count += 1
                    continue
                
                # Add to new cache
                chroma_cache.add_to_cache(item['query'], item['summary'])
                migrated_count += 1
                
                # Progress update
                if (i + 1) % 10 == 0:
                    print(f"   Processed {i + 1}/{len(old_cache)} items...")
                    
            except Exception as e:
                print(f"❌ Failed to migrate item {i}: {e}")
                failed_count += 1
        
        # Final statistics
        print(f"\n✅ Migration completed!")
        print(f"   Successfully migrated: {migrated_count} items")
        print(f"   Failed: {failed_count} items")
        print(f"   Total cache size: {chroma_cache.get_cache_stats()['total_queries']} queries")
        
        # Cleanup suggestion
        print(f"\n💡 Migration successful! You can now:")
        print(f"   1. Delete the old cache file: rm {OLD_CACHE_FILE}")
        print(f"   2. Keep the backup if needed: {BACKUP_CACHE_FILE}")
        print(f"   3. Start using your Flask app with ChromaDB!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Please check your old cache file and try again.")

def verify_migration():
    """
    Verify that the migration was successful
    """
    print("\n🔍 Verifying migration...")
    
    try:
        chroma_cache = ChromaDBCache()
        stats = chroma_cache.get_cache_stats()
        
        print(f"✅ ChromaDB cache is working!")
        print(f"   Total queries: {stats['total_queries']}")
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Database path: {stats['database_path']}")
        
        # Test a simple query
        test_result = chroma_cache.find_similar_query("test query", threshold=0.5)
        print(f"   Test query result: {'Found' if test_result[0] else 'Not found'}")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    print("🎯 ChromaDB Cache Migration Tool")
    print("=" * 40)
    
    # Run migration
    migrate_cache()
    
    # Verify migration
    verify_migration()
    
    print("\n🎉 Migration process completed!")
    print("Your Flask app is now ready to use ChromaDB cache.")