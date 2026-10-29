import re
import json
import subprocess
import chromadb
import ollama
from pathlib import Path

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


class Athenae:
    def __init__(self):
        client = chromadb.PersistentClient(path=DB_DIR)
        self.collection = client.get_collection(name=COLLECTION_NAME)
        self.history = []
        self.max_history_turns = 4
        self.history_file = Path("/home/skilipi/ai_rag_project/chat_history.json")
        self.load_history()

    def save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Could not save history: {e}")

    def load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def chunk_count(self):
        return self.collection.count()

    def list_books(self):
        all_data = self.collection.get(limit=100000, include=["metadatas"])
        return sorted(set(m["source"] for m in all_data["metadatas"]))

    def is_code_query(self, q):
        ql = q.lower()
        return any(kw in ql for kw in CODE_KEYWORDS)

    def try_calculate(self, q):
        q_clean = q.strip().rstrip("?").replace("^", "**")
        if MATH_PATTERN.match(q_clean.replace("^", "")):
            try:
                return eval(q_clean, {"__builtins__": {}}, {})
            except Exception:
                return None
        return None

    def retrieve(self, query, k=TOP_K, book_filter=None):
        resp = ollama.embeddings(model=EMBED_MODEL, prompt=query)
        where = {"source": book_filter} if book_filter else None
        return self.collection.query(query_embeddings=[resp["embedding"]], n_results=k, where=where)

    def filter_relevant(self, results, threshold=DISTANCE_THRESHOLD):
        docs, metas, dists = (results["documents"][0], results["metadatas"][0], results["distances"][0])
        kept_docs, kept_sources = [], []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist <= threshold:
                kept_docs.append(doc)
                kept_sources.append(meta["source"])
        return kept_docs, kept_sources

    def build_messages(self, query, kept_docs, kept_sources):
        if kept_docs:
            context = "\n\n---\n\n".join(f"[From: {s}]\n{d}" for d, s in zip(kept_docs, kept_sources))
            user_content = f"(Reference material from the user's library — ground your answer in this and cite the source:)\n{context}\n\nUser question: {query}"
        else:
            user_content = query

        messages = [{"role": "system", "content": IDENTITY}]
        recent = self.history[-(self.max_history_turns * 2):]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_content})
        return messages

    def ask(self, query, stream_callback=None, book_filter=None):
        """Returns (answer_text, kept_docs, kept_sources). stream_callback(token) called per chunk if given."""
        calc_result = self.try_calculate(query)
        if calc_result is not None:
            answer = str(calc_result)
            if stream_callback:
                stream_callback(answer)
            self.history.append({"role": "user", "content": query})
            self.history.append({"role": "assistant", "content": answer})
            return answer, [], []

        model = CODER_MODEL if self.is_code_query(query) else GENERAL_MODEL
        results = self.retrieve(query, book_filter=book_filter)
        kept_docs, kept_sources = self.filter_relevant(results)
        messages = self.build_messages(query, kept_docs, kept_sources)

        full_answer = ""
        stream = ollama.chat(model=model, messages=messages, stream=True)
        for chunk in stream:
            token = chunk["message"]["content"]
            full_answer += token
            if stream_callback:
                stream_callback(token)

        self.history.append({"role": "user", "content": query})
        self.history.append({"role": "assistant", "content": full_answer})
        self.save_history()
        return full_answer, kept_docs, kept_sources

    def clear_history(self):
        self.history = []
        self.save_history()

    def run_audit(self, path):
        """Returns combined text output of the audit for a single file or directory."""
        result = subprocess.run(
            ["python3", "/home/skilipi/ai_rag_project/scripts/audit.py", path],
            capture_output=True, text=True, timeout=300
        )
        return result.stdout + ("\n" + result.stderr if result.stderr else "")
