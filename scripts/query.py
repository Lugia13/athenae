import re
import chromadb
import ollama

DB_DIR = "/home/skilipi/ai_rag_project/chroma_db"
COLLECTION_NAME = "books"
EMBED_MODEL = "nomic-embed-text"
GENERAL_MODEL = "qwen2.5:3b-instruct-q4_K_M"
CODER_MODEL = "qwen2.5-coder:3b-instruct-q4_K_M"
TOP_K = 4
DISTANCE_THRESHOLD = 310.0

IDENTITY = """You are Athenae, a local AI assistant running entirely on the user's own machine.
If asked who you are, say: "I'm Athenae, your local AI assistant." Never mention Qwen, Alibaba, or any underlying model name.

If reference material from the user's book library is provided below, you MUST ground your answer in it and cite the source book by name. Do not contradict it or add unverified facts (dates, names, statistics) beyond what it states.

If no library material is provided, answer from your own knowledge across coding, math, physics, finance, and general science, but explicitly flag any specific dates, names, or statistics as "unverified — please confirm" since you cannot guarantee their accuracy from memory alone."""

CODE_KEYWORDS = ["code", "function", "script", "bug", "debug", "python", "javascript",
                  "c++", "algorithm", "program", "class ", "def ", "compile", "syntax", "refactor"]

MATH_PATTERN = re.compile(r'^[\d\s\+\-\*/\.\(\)\^%]+$')

def is_code_query(q):
    ql = q.lower()
    return any(kw in ql for kw in CODE_KEYWORDS)

def try_calculate(q):
    q_clean = q.strip().rstrip("?").replace("^", "**")
    if MATH_PATTERN.match(q_clean.replace("^", "")):
        try:
            result = eval(q_clean, {"__builtins__": {}}, {})
            return result
        except Exception:
            return None
    return None

def retrieve(collection, query, k=TOP_K):
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    results = collection.query(query_embeddings=[resp["embedding"]], n_results=k)
    return results

def filter_relevant(results, threshold=DISTANCE_THRESHOLD):
    docs, metas, dists = (results["documents"][0], results["metadatas"][0], results["distances"][0])
    kept_docs, kept_sources = [], []
    for doc, meta, dist in zip(docs, metas, dists):
        if dist <= threshold:
            kept_docs.append(doc)
            kept_sources.append(meta["source"])
    return kept_docs, kept_sources

def build_messages(query, kept_docs, kept_sources):
    if kept_docs:
        context = "\n\n---\n\n".join(f"[From: {s}]\n{d}" for d, s in zip(kept_docs, kept_sources))
        user_content = f"(Reference material from the user's library — ground your answer in this and cite the source:)\n{context}\n\nUser question: {query}"
    else:
        user_content = query
    return [
        {"role": "system", "content": IDENTITY},
        {"role": "user", "content": user_content},
    ]

def main():
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_collection(name=COLLECTION_NAME)
    print(f"Athenae ready. Library: {collection.count()} chunks loaded.\n")
    print("Type your question ('quit' to exit, 'audit <path>' to scan code).\n")

    while True:
        query = input("You: ").strip()
        if query.lower() in ("quit", "exit"):
            break
        if not query:
            continue

        if query.lower().startswith("audit "):
            import subprocess
            target = query[6:].strip()
            print(f"\n[Running audit on {target} ...]\n")
            subprocess.run(["python3", "/home/skilipi/ai_rag_project/scripts/audit.py", target])
            continue

        calc_result = try_calculate(query)
        if calc_result is not None:
            print(f"\nAthenae: {calc_result}\n")
            continue

        model = CODER_MODEL if is_code_query(query) else GENERAL_MODEL

        results = retrieve(collection, query)
        kept_docs, kept_sources = filter_relevant(results)
        messages = build_messages(query, kept_docs, kept_sources)

        print(f"\nAthenae: ", end="", flush=True)
        stream = ollama.chat(model=model, messages=messages, stream=True)
        for chunk in stream:
            print(chunk["message"]["content"], end="", flush=True)
        print("\n")

        if kept_docs:
            print("─" * 50)
            print("Raw excerpts used (verify facts against these):")
            for doc, src in zip(kept_docs, kept_sources):
                snippet = doc[:220].replace("\n", " ").strip()
                print(f"\n  [{src}]")
                print(f"  \"{snippet}...\"")
            print("─" * 50 + "\n")

if __name__ == "__main__":
    main()
