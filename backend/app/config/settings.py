from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Project Root
BASE_DIR = Path(__file__).resolve().parents[3]

# -------------------------
# LLM Configuration
# -------------------------

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b"
)

# -------------------------
# Embedding Configuration
# -------------------------

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2"
)

# -------------------------
# Vector Database
# -------------------------

CHROMA_PATH = os.getenv(
    "CHROMA_PATH",
    str(BASE_DIR / "chroma_db")
)

COLLECTION_NAME = "wikipedia_articles"

# -------------------------
# Chunking
# -------------------------

CHUNK_SIZE = int(
    os.getenv("CHUNK_SIZE", 800)
)

CHUNK_OVERLAP = int(
    os.getenv("CHUNK_OVERLAP", 100)
)

TOP_K = int(
    os.getenv("TOP_K", 5)
)