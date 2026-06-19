from fastapi import FastAPI

from backend.app.api.routes import router

app = FastAPI(
    title="Wikipedia RAG Chatbot",
    version="1.0.0",
)

app.include_router(router)