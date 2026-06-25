from typing import List, Optional

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = None


class ImageItem(BaseModel):
    url: str
    caption: str


class AskResponse(BaseModel):
    answer: str
    article: str
    wikipedia_url: str
    sources: List[str]
    images: List[ImageItem] = []
    cache_hit: bool
    response_time: float
    model: str
    spelling_corrected: bool = False
    matched_query: Optional[str] = None