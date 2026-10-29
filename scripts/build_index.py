from config import BASE_DIR
import os
import re
from pathlib import Path
import chromadb
import ollama
from tqdm import tqdm

TEXT_DIR = str(BASE_DIR / "extracted_text")
DB_DIR = str(BASE_DIR / "chroma_db")
COLLECTION_NAME = "books"
EMBED_MODEL = "nomic-embed-text"

CHUNK_SIZE = 1000      # characters per chunk
CHUNK_OVERLAP = 150    # overlap between chunks

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r'\n{3,}', '\n\n', text)  # collapse huge gaps
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += size - overlap
    return chunks

def main():
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    txt_files = list(Path(TEXT_DIR).glob("*.txt"))
    print(f"Found {len(txt_files)} text files to index")

    total_chunks = 0
    for txt_path in txt_files:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        book_name = txt_path.stem

        # Check if already indexed (skip re-processing)
        existing = collection.get(where={"source": book_name}, limit=1)
        if existing["ids"]:
            print(f"Skipping (already indexed): {book_name}")
            continue

        print(f"Indexing '{book_name}' -> {len(chunks)} chunks")
        batch_ids, batch_docs, batch_metas, batch_embeds = [], [], [], []

        for i, chunk in enumerate(tqdm(chunks, desc=book_name[:40], leave=False)):
            try:
                resp = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)
                embedding = resp["embedding"]
            except Exception as e:
                print(f"  embed error on chunk {i}: {e}")
                continue

            batch_ids.append(f"{book_name}_{i}")
            batch_docs.append(chunk)
            batch_metas.append({"source": book_name, "chunk_index": i})
            batch_embeds.append(embedding)

            # write in batches of 50 to avoid memory spikes
            if len(batch_ids) >= 50:
                collection.add(ids=batch_ids, documents=batch_docs,
                                metadatas=batch_metas, embeddings=batch_embeds)
                total_chunks += len(batch_ids)
                batch_ids, batch_docs, batch_metas, batch_embeds = [], [], [], []

        if batch_ids:
            collection.add(ids=batch_ids, documents=batch_docs,
                            metadatas=batch_metas, embeddings=batch_embeds)
            total_chunks += len(batch_ids)

    print(f"\nDone. Total chunks indexed this run: {total_chunks}")
    print(f"Total chunks in collection: {collection.count()}")

if __name__ == "__main__":
    main()
