# 📚 Wikipedia RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers user questions using Wikipedia articles. The application retrieves relevant Wikipedia content, generates embeddings, stores them in ChromaDB, and uses a local Qwen model through Ollama to generate grounded responses.

---

## Features

- 🔍 Wikipedia article retrieval
- 🧹 Text cleaning and preprocessing
- ✂️ Intelligent text chunking
- 🧠 SentenceTransformer embeddings
- 🗄️ ChromaDB vector database
- 🤖 Local LLM inference using Ollama (Qwen)
- ⚡ FastAPI backend
- 🎨 React + Vite frontend
- 📖 Wikipedia source links
- 💾 Cache support for indexed articles

---

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- SentenceTransformers
- ChromaDB
- Ollama
- Qwen3:4B
- wikipedia-api
- LangChain Text Splitters

### Frontend
- React
- Vite
- Axios
- CSS

---

## Project Structure

```
wikipedia-rag-chatbot/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── vectorstore/
│   ├── utils/
│   └── main.py
│
├── frontend/
│   ├── src/
│   └── public/
│
├── chroma_db/
├── requirements.txt
└── README.md
```

---

## Installation

### Clone

```bash
git clone <repository-url>
cd wikipedia-rag-chatbot
```

---

### Backend

Create a virtual environment

```bash
python3 -m venv .venv
```

Activate

Mac/Linux

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

### Start Ollama

Pull the model

```bash
ollama pull qwen3:4b
```

Run Ollama

```bash
ollama serve
```

---

### Start Backend

```bash
python3 -m uvicorn backend.app.main:app --reload
```

Backend

```
http://127.0.0.1:8000
```

Swagger Docs

```
http://127.0.0.1:8000/docs
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend

```
http://localhost:5173
```

---

## How It Works

1. User asks a question.
2. Wikipedia article is retrieved.
3. Article is cleaned.
4. Text is split into chunks.
5. Embeddings are generated.
6. Chunks are stored in ChromaDB.
7. Relevant chunks are retrieved.
8. Context is sent to Qwen via Ollama.
9. Answer is returned with Wikipedia source.

---

## Example

Question

```
What is Python?
```

Output

```
Answer:
Python is a high-level programming language...

Article:
Python (programming language)

Response Time:
1.24 sec

Cache:
Hit
```

---

## Future Improvements

- Streaming responses
- Conversation memory
- Multiple document retrieval
- Better reranking
- Docker support
- Authentication
- Deployment on cloud

---

## Author

Vinamra Lilaria