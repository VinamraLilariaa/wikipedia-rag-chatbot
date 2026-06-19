from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import AskRequest, AskResponse
from backend.app.services.wikipedia_service import WikipediaService

router = APIRouter()

wiki = WikipediaService()


@router.get("/")
def root():
    return {
        "message": "Wikipedia RAG Chatbot API is running!"
    }


@router.get("/health")
def health():
    return {
        "status": "healthy"
    }


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):

    try:

        article = wiki.get_article(request.question)

        return AskResponse(
            title=article["title"],
            url=article["url"],
            content=article["content"][:2000]
        )

    except Exception as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )