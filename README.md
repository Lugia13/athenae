# Athenae

Athenae is a fully local AI assistant combining retrieval augmented generation, general purpose reasoning, and automated code auditing. Everything runs offline on consumer hardware using open source models, with no cloud API calls and no data leaving the machine.

## What it does

Athenae lets you build a private knowledge base from your own PDF documents. It extracts and chunks text, embeds it into a local vector database, and retrieves relevant passages at query time to ground its answers. When your documents contain relevant information, Athenae cites the exact source and excerpt used. When they do not, it falls back to general knowledge while flagging specific facts, dates, and figures as unverified, since small local language models can produce confident sounding but incorrect details.

Beyond document retrieval, Athenae also functions as a general assistant for coding and explanation tasks, automatically routing programming questions to a code specialized model. It includes a built in code auditing mode that runs static analysis tools and then explains the findings in plain language with suggested fixes.

## Architecture

The system is composed of several independent pieces that communicate through local processes rather than cloud services.

Document ingestion extracts text from PDF files using PyMuPDF, then splits it into overlapping chunks sized for embedding.

Embedding and storage uses a local embedding model served through Ollama, with ChromaDB as the persistent vector store on disk.

Retrieval computes the embedding of each incoming question, searches the vector store for the closest matching chunks, and filters results by a distance threshold so that irrelevant results are excluded rather than forced into every answer.

Generation routes the question and any retrieved context to a local language model served through Ollama, using a general purpose model for most questions and a code specialized model when the question concerns programming.

Code auditing runs bandit and ruff in a separate isolated Python environment to avoid dependency conflicts with the main application, then passes the structured findings to the language model for a plain language explanation with severity preserved exactly as reported by the tools, rather than left to the model to infer.

The interface is a native desktop application built with Tkinter, including conversation history that persists between sessions, a dropdown to restrict retrieval to a specific document, and export options for conversations and audit reports.

## Requirements

Everything here runs on modest consumer hardware with no GPU required, though a GPU will significantly speed up generation if available. The project relies entirely on free and open source tools.

Python 3.11 or newer, Ollama for running local language models, and the Python packages listed in requirements.txt.

## Setup

Clone the repository and create a virtual environment.

git clone https://github.com/Lugia13/athenae.git
cd athenae
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Install Ollama separately following the instructions at ollama.com, then pull the required models.

ollama pull nomic-embed-text
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama pull qwen2.5-coder:3b-instruct-q4_K_M

Create a second isolated environment for the code auditing tools to avoid dependency conflicts with the main application.

python3 -m venv audit_venv
source audit_venv/bin/activate
pip install bandit ruff
deactivate

## Usage

Place PDF documents you want indexed into a folder of your choice, then update the path in scripts/extract_pdfs.py to point to it.

Extract text from your documents.

python scripts/extract_pdfs.py

Build the vector index.

python scripts/build_index.py

Launch the graphical interface.

python scripts/gui.py

## Honest limitations

This project intentionally uses small quantized models so that it runs entirely on CPU only consumer hardware without specialized infrastructure. This is a meaningful tradeoff. Small models are fluent and often genuinely useful for explanation and coding tasks, but they are not reliable for precise facts such as dates, names, or statistics, even when given correct source material to work from. Always verify specific factual claims against the original source rather than trusting the generated summary alone. The project is best understood as a personal research and development tool exploring what is achievable entirely offline on modest hardware, not as a production grade or professionally audited system.

## License

MIT
## Author

Oussama Saddati
Portfolio: oussamasaddati.vercel.app
