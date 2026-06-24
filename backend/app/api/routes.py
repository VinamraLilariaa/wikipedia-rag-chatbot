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

    try:

        if rag is None:
            print("Creating RAG Service...")
            rag = RAGService()
            print("RAG Service Created!")

        return rag.ask(request.question)

    except Exception as e:
        logger.exception("Error while processing /ask")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )