from typing import List

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    article: str
    wikipedia_url: str
    sources: List[str]
    cache_hit: bool
    response_time: float
    model: str