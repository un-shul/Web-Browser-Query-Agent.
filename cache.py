import os
import pickle
from sentence_transformers import SentenceTransformer, util

# Load embedding model
model = SentenceTransformer("embedding_model")

# Path to cache file
CACHE_FILE = "query_cache.pkl"

# Load existing cache or create empty
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "rb") as f:
        cache = pickle.load(f)
else:
    cache = []

# Each entry in cache: {"query": str, "embedding": np.array, "summary": str}

def find_similar_query(new_query, threshold=0.75):
    new_embedding = model.encode([new_query])[0]
    
    for item in cache:
        sim = util.cos_sim(new_embedding, item["embedding"])[0].item()
        # print(f"🧪 Similarity with: \"{item['query']}\" = {sim:.2f}")
        if sim >= threshold:
            return item["summary"], sim

    return None, None


def add_to_cache(query, summary):
    embedding = model.encode([query])[0]
    cache.append({
        "query": query,
        "embedding": embedding,
        "summary": summary
    })
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)
