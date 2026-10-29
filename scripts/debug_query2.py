from config import BASE_DIR
import chromadb
import ollama

DB_DIR = str(BASE_DIR / "chroma_db")
COLLECTION_NAME = "books"
EMBED_MODEL = "nomic-embed-text"

client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_collection(name=COLLECTION_NAME)

test_queries = [
    "what is superconductor",
    "superconductivity",
    "definir l'epitaxie",
    "epitaxie semiconducteur",
]

for q in test_queries:
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=q)
    results = collection.query(query_embeddings=[resp["embedding"]], n_results=5)
    print(f"\nQuery: '{q}'")
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        preview = doc[:80].replace("\n", " ")
        print(f"  dist={dist:.2f}  source={meta['source'][:35]:35s}  preview: {preview}")
