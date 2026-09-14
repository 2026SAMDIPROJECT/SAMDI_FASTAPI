"""텍스트 -> 벡터 변환. provider 설정에 따라 OpenAI 또는 로컬 모델을 쓴다."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from app.config import settings


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 비어 있습니다. .env를 확인하세요.")
    return OpenAI(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    name = settings.embed_model
    if name.startswith("text-embedding"):  # OpenAI 기본값이면 로컬용으로 교체
        name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    return SentenceTransformer(name)


def embed(texts: List[str]) -> List[List[float]]:
    """문자열 리스트를 임베딩 벡터 리스트로 변환한다."""
    if not texts:
        return []

    if settings.embed_provider == "local":
        model = _local_model()
        return [v.tolist() for v in model.encode(texts, normalize_embeddings=True)]

    resp = _openai_client().embeddings.create(model=settings.embed_model, input=texts)
    return [d.embedding for d in resp.data]
