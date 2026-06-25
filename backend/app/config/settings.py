import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Models
GROQ_MODEL = "llama3-70b-8192"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Paths - Using /tmp for HuggingFace Cloud stability
# This avoids permission errors when the server tries to write the database
CHROMA_PATH = "/tmp/chroma_db_production"
COLLECTION_NAME = "wiki_intel_rag"

# Scraping Settings
MAX_CHUNK_LENGTH = 1200
CONTEXT_BUFFER = 80000 # 80k characters for high-context grounding