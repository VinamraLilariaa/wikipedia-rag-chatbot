import logging
import traceback

from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import AskRequest, AskResponse
from backend.app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()

rag = None


@router.get("/health")
def health():
    return {
        "status": "healthy"
    }


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask(request: AskRequest):

    global rag

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    try:

        if rag is None:
            print("Creating RAG Service...")
            rag = RAGService()
            print("RAG Service Created!")

        return rag.ask(question)

    except ValueError as e:
        # Expected, user-facing failures: e.g. no matching Wikipedia article.
        logger.warning(f"No result for question '{question}': {e}")

        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        logger.exception("Error while processing /ask")
        traceback.print_exc()

        # Reveal the actual error message temporarily to debug the server environment
        error_msg = str(e) or "An unknown error occurred."
        raise HTTPException(
            status_code=500,
            detail=f"Error: {error_msg}. Check your API keys and server logs.",
        )