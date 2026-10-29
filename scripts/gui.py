import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import threading
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from athenae_core import Athenae

class AthenaeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Athenae — Local AI Assistant")
        self.root.geometry("900x700")
        self.root.configure(bg="#1a1a2e")

        self.athenae = Athenae()

        # Header
        header = tk.Frame(root, bg="#16213e", height=50)
        header.pack(fill=tk.X)
        tk.Label(header, text="ATHENAE", font=("Arial", 18, "bold"),
                 fg="#4ecca3", bg="#16213e").pack(side=tk.LEFT, padx=15, pady=10)
        self.status_label = tk.Label(header, text=f"Library: {self.athenae.chunk_count()} chunks",
                                      font=("Arial", 10), fg="#aaaaaa", bg="#16213e")
        self.status_label.pack(side=tk.RIGHT, padx=15)

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, bg="#0f0f1e", fg="#e0e0e0",
            font=("Consolas", 11), state=tk.DISABLED, padx=10, pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_display.tag_config("user", foreground="#4ecca3", font=("Consolas", 11, "bold"))
        self.chat_display.tag_config("athenae", foreground="#e94560", font=("Consolas", 11, "bold"))
        self.chat_display.tag_config("source", foreground="#888888", font=("Consolas", 9, "italic"))

        # Input area
        input_frame = tk.Frame(root, bg="#1a1a2e")
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.input_box = tk.Entry(input_frame, font=("Consolas", 12), bg="#16213e", fg="#ffffff", insertbackground="white")
        self.input_box.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.input_box.bind("<Return>", lambda e: self.send_message())

        tk.Button(input_frame, text="Send", command=self.send_message,
                  bg="#4ecca3", fg="#0f0f1e", font=("Arial", 10, "bold"), relief=tk.FLAT, padx=15).pack(side=tk.LEFT)

        # Toolbar
        toolbar = tk.Frame(root, bg="#1a1a2e")
        toolbar.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(toolbar, text="Audit File/Folder", command=self.audit_dialog,
                  bg="#e94560", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(toolbar, text="Clear Chat", command=self.clear_chat,
                  bg="#333355", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(toolbar, text="Export Conversation", command=self.export_chat,
                  bg="#333355", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(toolbar, text="Filter book:", bg="#1a1a2e", fg="#aaaaaa").pack(side=tk.LEFT, padx=(10, 5))
        self.book_var = tk.StringVar(value="All books")
        books = ["All books"] + self.athenae.list_books()
        self.book_dropdown = tk.OptionMenu(toolbar, self.book_var, *books)
        self.book_dropdown.config(bg="#333355", fg="white", relief=tk.FLAT)
        self.book_dropdown.pack(side=tk.LEFT)

        self.append_text("Athenae", "Ready. Ask me anything, or use the Audit button for code review.\n", "athenae")
        self._load_prior_history()

    def _load_prior_history(self):
        if self.athenae.history:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "--- Previous session restored ---\n\n")
            for msg in self.athenae.history:
                label = "You" if msg["role"] == "user" else "Athenae"
                tag = "user" if msg["role"] == "user" else "athenae"
                self.chat_display.insert(tk.END, f"{label}: ", tag)
                self.chat_display.insert(tk.END, msg["content"] + "\n\n")
            self.chat_display.config(state=tk.DISABLED)

    def append_text(self, label, text, tag):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{label}: ", tag)
        self.chat_display.insert(tk.END, text + "\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def append_sources(self, docs, sources):
        if not docs:
            return
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Sources:\n", "source")
        for doc, src in zip(docs, sources):
            snippet = doc[:150].replace("\n", " ").strip()
            self.chat_display.insert(tk.END, f"  [{src}] \"{snippet}...\"\n", "source")
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def send_message(self):
        query = self.input_box.get().strip()
        if not query:
            return
        self.input_box.delete(0, tk.END)
        self.append_text("You", query, "user")

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Athenae: ", "athenae")
        self.chat_display.config(state=tk.DISABLED)

        threading.Thread(target=self._run_query, args=(query,), daemon=True).start()

    def _run_query(self, query):
        def on_token(token):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, token)
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)

        selected = self.book_var.get()
        book_filter = None if selected == "All books" else selected
        answer, docs, sources = self.athenae.ask(query, stream_callback=on_token, book_filter=book_filter)
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.append_sources(docs, sources)

    def audit_dialog(self):
        path = filedialog.askopenfilename(title="Select file to audit") or filedialog.askdirectory(title="Or select a folder")
        if not path:
            return
        self.append_text("Athenae", f"Running audit on {path} ... (this may take a moment)", "athenae")
        threading.Thread(target=self._run_audit, args=(path,), daemon=True).start()

    def _run_audit(self, path):
        output = self.athenae.run_audit(path)
        self.last_audit_output = output
        self.last_audit_path = path
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, output + "\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.root.after(0, self._offer_audit_export)

    def _offer_audit_export(self):
        if messagebox.askyesno("Export Report", "Save this audit as a Markdown report?"):
            self.export_audit_report()

    def export_audit_report(self):
        if not hasattr(self, "last_audit_output"):
            messagebox.showinfo("No audit", "Run an audit first.")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"audit_report_{timestamp}.md"
        path = filedialog.asksaveasfilename(defaultextension=".md", initialfile=default_name)
        if path:
            report = f"# Audit Report\n\nTarget: `{self.last_audit_path}`\nGenerated: {datetime.now().isoformat()}\n\n---\n\n{self.last_audit_output}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(report)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")

    def clear_chat(self):
        self.athenae.clear_history()
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.append_text("Athenae", "Conversation cleared.", "athenae")

    def export_chat(self):
        content = self.chat_display.get(1.0, tk.END)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"athenae_chat_{timestamp}.md"
        path = filedialog.asksaveasfilename(defaultextension=".md", initialfile=default_name)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Exported", f"Conversation saved to:\n{path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AthenaeGUI(root)
    root.mainloop()
