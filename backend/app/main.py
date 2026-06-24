from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

app.include_router(router)

app.mount("/assets", StaticFiles(directory="backend/static/assets"), name="assets")


@app.get("/{full_path:path}")
async def frontend(full_path: str):
    return FileResponse("backend/static/index.html")