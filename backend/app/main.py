from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.app.api.routes import router

app = FastAPI(
    title="Wikipedia RAG Chatbot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API endpoints
app.include_router(router, prefix="/api")

# React static assets
app.mount(
    "/assets",
    StaticFiles(directory="backend/static/assets"),
    name="assets",
)


@app.get("/")
async def serve_frontend():
    return FileResponse("backend/static/index.html")


@app.get("/{full_path:path}")
async def catch_all(full_path: str):

    file_path = os.path.join("backend/static", full_path)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    return FileResponse("backend/static/index.html")