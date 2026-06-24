---
title: Wikipedia RAG Chatbot
emoji: 📚
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 📚 Wikipedia RAG Chatbot

A full-stack Retrieval-Augmented Generation (RAG) chatbot that retrieves information from Wikipedia, stores embeddings in ChromaDB, and generates grounded answers using Groq Llama.

## Features

- 🔍 Automatic Wikipedia article retrieval
- ✂️ Intelligent text chunking
- 🧠 SentenceTransformer embeddings
- 💾 ChromaDB vector database
- ⚡ Groq Llama inference
- 📖 Retrieved context display
- 🚀 FastAPI backend
- ⚛️ React + Vite frontend
- 🐳 Docker deployment
- ☁️ Hugging Face Spaces compatible

## Tech Stack

### Backend

- FastAPI
- ChromaDB
- Sentence Transformers
- Groq API

### Frontend

- React
- Vite
- Axios

### Deployment

- Docker
- Hugging Face Spaces

## Environment Variables

Create a `.env` file containing:

```env
GROQ_API_KEY=your_groq_api_key
LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
```

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
python -m uvicorn backend.app.main:app --reload
```

Run frontend:

```bash
cd frontend
npm install
npm run dev
```

## Docker

Build:

```bash
docker build -t wikipedia-rag .
```

Run:

```bash
docker run -p 7860:7860 wikipedia-rag
```

## License

MIT License