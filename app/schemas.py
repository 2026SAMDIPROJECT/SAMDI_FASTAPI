"""API 요청/응답 스키마."""
from typing import List, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(default="default", description="대화 세션 식별자")
    message: str = Field(..., min_length=1, max_length=1000, description="직원(사용자) 발화")
    scene: str = Field(default="일반 매장", description="상황/장소 (예: 카페, 편의점)")
    difficulty: Literal["easy", "normal", "hard"] = "normal"


class Source(BaseModel):
    type: str
    place: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    sources: List[Source]
    ended: bool


class SearchHit(BaseModel):
    document: str
    score: float
