# 📚 Wikipedia RAG Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot that answers user questions using Wikipedia as its knowledge source.

The application retrieves relevant Wikipedia articles, preprocesses and chunks the text, generates semantic embeddings using SentenceTransformers, stores them in ChromaDB, retrieves the most relevant context through vector similarity search, and finally generates a grounded answer using the **Groq API**.

---

# 🚀 Features

- 🔍 Wikipedia article retrieval
- 🧹 Text cleaning and preprocessing
- ✂️ Intelligent text chunking
- 🧠 SentenceTransformer embeddings
- 🗄️ ChromaDB vector database
- 🤖 Groq LLM Integration
- ⚡ FastAPI backend
- 🎨 React + Vite frontend
- 📖 Wikipedia source links
- 💾 Cached article indexing
- 🔄 Semantic retrieval using vector search

---

# 🏗️ Architecture

```
                    User
                      │
                      ▼
               React Frontend
                      │
              HTTP POST /ask
                      │
                      ▼
                 FastAPI Backend
                      │
                      ▼
                 RAGService
                      │
      ┌───────────────┼───────────────┐
      │               │               │
Wikipedia       Text Cleaner     Chunker
      │               │               │
      └───────────────┴───────────────┘
                      │
                      ▼
         SentenceTransformer Embeddings
                      │
                      ▼
                 ChromaDB
                      │
                      ▼
          Relevant Context Retrieval
                      │
                      ▼
               Groq LLM API
                      │
                      ▼
                Generated Answer
                      │
                      ▼
               React Frontend
```

---

# 🛠 Tech Stack

## Backend

- Python 3.11
- FastAPI
- ChromaDB
- SentenceTransformers
- Wikipedia API
- Groq API
- HTTPX
- LangChain Text Splitters

## Frontend

- React
- Vite
- Axios
- CSS

---

# 📂 Project Structure

```
wikipedia-rag-chatbot/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── cache/
│   │   ├── config/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── vectorstore/
│   │   └── main.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── chroma_db/
├── requirements.txt
├── README.md
└── .env
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone <repository-url>
cd wikipedia-rag-chatbot
```

---

## 2. Create Virtual Environment

```bash
python3 -m venv .venv
```

Activate it

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
LLM_PROVIDER=groq

GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=llama-3.3-70b-versatile

EMBEDDING_MODEL=all-MiniLM-L6-v2

CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=5
```

---

## 5. Start the Backend

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

## 6. Start the Frontend

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

# 🔄 How It Works

1. User enters a question.
2. FastAPI receives the request.
3. Wikipedia is searched for the most relevant article.
4. The article is downloaded.
5. The text is cleaned.
6. The article is split into chunks.
7. SentenceTransformer generates embeddings.
8. Embeddings are stored in ChromaDB.
9. The user's question is converted into an embedding.
10. ChromaDB retrieves the most relevant chunks.
11. Retrieved context is sent to the Groq LLM.
12. The LLM generates an answer grounded in the retrieved Wikipedia context.
13. The answer is returned to the React frontend.

---

# 💡 Example

## Question

```
What is Python?
```

## Response

```
Answer:
Python is a high-level, general-purpose programming language...

Article:
Python (programming language)

Response Time:
0.82 sec

Cache:
Hit
```

---

# 📌 API Endpoints

| Method | Endpoint | Description |
|----------|----------|-------------|
| GET | `/` | API Status |
| GET | `/health` | Health Check |
| POST | `/ask` | Ask a Question |

---

# 🎯 Future Improvements

- Hybrid Retrieval (Keyword + Semantic Search)
- Query Correction & Fuzzy Matching
- Streaming Responses
- Conversation Memory
- Multi-document Retrieval
- Cross-Encoder Reranking
- Docker Support
- Cloud Deployment (Render + Vercel)
- Authentication
- User Chat History

---

# 📸 Screenshots

_Add screenshots of the application here._

Example:

- Home Page
- Generated Answer
- Retrieved Context

---

# 👨‍💻 Authors

- Tanav Lilaria
- Vinamra Lilaria

---

# 📜 License

This project is licensed under the MIT License.

---

# ⭐ Acknowledgements

- Wikipedia
- FastAPI
- React
- ChromaDB
- SentenceTransformers
- Groq
- Hugging Face