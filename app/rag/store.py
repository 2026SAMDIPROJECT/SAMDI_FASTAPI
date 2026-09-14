"""ChromaDB 벡터 스토어 래퍼: 적재(build_index)와 검색(search)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

from app.config import settings
from app.rag.embeddings import embed


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    return client.get_or_create_collection(
        name=settings.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def case_to_document(case: Dict[str, Any]) -> str:
    """검색 단위 텍스트로 변환. 이 포맷이 검색 품질을 좌우한다."""
    lines = " / ".join(case.get("lines", []))
    return (
        f"유형: {case['type']}\n"
        f"장소: {case['place']}\n"
        f"발동 상황: {case['trigger']}\n"
        f"행동 패턴: {case['behavior']}\n"
        f"대표 대사: {lines}\n"
        f"고조 방식: {case.get('escalation', '')}\n"
        f"약점: {case.get('weakness', '')}"
    )


def load_cases(path: Optional[str] = None) -> List[Dict[str, Any]]:
    p = Path(path or settings.data_path)
    if not p.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {p}")

    cases: List[Dict[str, Any]] = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{p}:{i} JSON 파싱 실패 - {e}") from e
    return cases


def build_index(path: Optional[str] = None, batch_size: int = 32) -> int:
    """JSONL을 읽어 임베딩 후 컬렉션에 upsert 한다. 적재 건수를 반환."""
    cases = load_cases(path)
    col = get_collection()

    ids = [c["id"] for c in cases]
    docs = [case_to_document(c) for c in cases]
    metas = [
        {
            "type": c["type"],
            "place": c["place"],
            "lines": " / ".join(c.get("lines", [])),
            "escalation": c.get("escalation", ""),
        }
        for c in cases
    ]

    for i in range(0, len(docs), batch_size):
        chunk = slice(i, i + batch_size)
        col.upsert(
            ids=ids[chunk],
            documents=docs[chunk],
            metadatas=metas[chunk],
            embeddings=embed(docs[chunk]),
        )
    return len(docs)


def search(query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
    """질의와 가장 비슷한 진상 사례를 k개 반환한다."""
    k = k or settings.top_k
    col = get_collection()
    count = col.count()
    if count == 0:
        return []

    res = col.query(
        query_embeddings=embed([query]),
        n_results=min(k, count),
        include=["documents", "metadatas", "distances"],
    )
    hits: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"document": doc, "metadata": meta, "score": round(1.0 - dist, 4)})
    return hits
