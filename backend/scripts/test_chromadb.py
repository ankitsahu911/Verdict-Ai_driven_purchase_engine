import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

CHROMA_HOST = os.getenv("CHROMA_HOST")

if CHROMA_HOST:
    import chromadb

    print(f"Connecting to hosted ChromaDB at {CHROMA_HOST}")
    client = chromadb.HttpClient(host=CHROMA_HOST)
else:
    import chromadb

    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Using local PersistentClient at {DATA_DIR}")
    client = chromadb.PersistentClient(path=str(DATA_DIR))

COLLECTION_NAME = "verdict-test-throwaway"

try:
    client.delete_collection(COLLECTION_NAME)
    print(f"  Deleted leftover collection `{COLLECTION_NAME}`")
except Exception:
    pass

collection = client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,
)

VECTOR_DIM = 4
doc_id = str(uuid.uuid4())

embedding = [0.1, 0.2, 0.3, 0.4]
metadata = {"label": "test-vector", "source": "verdict-infra-check"}

print(f"  Adding vector id={doc_id}  embedding={embedding}")
collection.add(
    ids=[doc_id],
    embeddings=[embedding],
    metadatas=[metadata],
)

query_vector = [0.15, 0.25, 0.35, 0.45]

results = collection.query(query_embeddings=[query_vector], n_results=1)

matched_id = results["ids"][0][0]
matched_distance = results["distances"][0][0]
matched_metadata = results["metadatas"][0][0]

print(f"  Nearest neighbour: id={matched_id}")
print(f"  Distance:          {matched_distance:.4f}")
print(f"  Metadata:          {matched_metadata}")

assert matched_id == doc_id, f"Expected match on {doc_id}, got {matched_id}"
print("  Match verified")

client.delete_collection(COLLECTION_NAME)
print(f"  Cleaned up collection `{COLLECTION_NAME}`")

print("\nChromaDB test PASSED")
