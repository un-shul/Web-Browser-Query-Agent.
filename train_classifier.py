import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
import pickle

# Load dataset
df = pd.read_csv("augmented_query_dataset.csv")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Generate embeddings
embeddings = model.encode(df["query"].tolist())

# Convert labels
labels = df["label"].map({"valid": 1, "invalid": 0}).values

# Train classifier on full data
clf = LogisticRegression(max_iter=1000)
clf.fit(embeddings, labels)

# Save classifier
with open("classifier.pkl", "wb") as f:
    pickle.dump(clf, f)

# Save embedding model
model.save("embedding_model")

print("✅ Trained on full data. Classifier and embedding model saved.")
