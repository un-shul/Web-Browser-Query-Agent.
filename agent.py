from sentence_transformers import SentenceTransformer
import pickle

# Load classifier and embedding model (once at startup)
model = SentenceTransformer("embedding_model")
with open("classifier.pkl", "rb") as f:
    clf = pickle.load(f)

def classify_query(query: str) -> str:
    embedding = model.encode([query])[0]
    prediction = clf.predict([embedding])[0]
    return "valid" if prediction == 1 else "invalid"
