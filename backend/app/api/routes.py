import logging
import traceback

from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import AskRequest, AskResponse
from backend.app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()

rag = RAGService()


@router.get("/")
def root():
    return {
        "message": "Wikipedia RAG Chatbot API"
    }


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

    try:
        return rag.ask(request.question)

    except Exception as e:
        logger.exception("Error while processing /ask")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )