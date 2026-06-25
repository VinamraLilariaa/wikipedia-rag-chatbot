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

        return rag.ask(question, history=request.history)

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

        # Production error message: Clean, helpful, and non-technical
        raise HTTPException(
            status_code=500,
            detail="The knowledge service is temporarily overwhelmed. Please try again in a few moments.",
        )