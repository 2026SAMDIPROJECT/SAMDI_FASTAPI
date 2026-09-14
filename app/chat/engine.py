"""RAG 검색 -> 페르소나 프롬프트 -> LLM 호출로 이어지는 대화 엔진."""
from __future__ import annotations

from collections import defaultdict, deque
from functools import lru_cache
from typing import Any, Deque, Dict, List

from app.chat.persona import build_system_prompt
from app.config import settings
from app.rag.store import search

# 세션별 대화 기록 (프로세스 메모리. 운영에서는 Redis/DB로 교체할 것)
_HISTORY: Dict[str, Deque[Dict[str, str]]] = defaultdict(
    lambda: deque(maxlen=settings.max_history)
)

EXIT_WORDS = {"그만", "종료", "나가기", "exit", "quit"}


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _anthropic_client():
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _call_llm(system: str, messages: List[Dict[str, str]]) -> str:
    if settings.llm_provider == "anthropic":
        resp = _anthropic_client().messages.create(
            model=settings.chat_model,
            system=system,
            messages=messages,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    resp = _openai_client().chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def reset(session_id: str) -> None:
    _HISTORY.pop(session_id, None)


def history(session_id: str) -> List[Dict[str, str]]:
    return list(_HISTORY[session_id])


def chat(
    session_id: str,
    message: str,
    scene: str = "일반 매장",
    difficulty: str = "normal",
) -> Dict[str, Any]:
    """사용자 발화를 받아 진상 캐릭터의 답변을 만든다."""
    if message.strip() in EXIT_WORDS:
        reset(session_id)
        return {"reply": "…됐어요, 갑니다. 다음엔 잘 좀 해요.", "sources": [], "ended": True}

    # 1) 검색: 직전 대화 맥락 + 이번 발화로 질의를 구성해야 흐름이 유지된다
    recent = " ".join(m["content"] for m in list(_HISTORY[session_id])[-2:])
    query = f"{scene} {recent} {message}".strip()
    hits = search(query)

    # 2) 프롬프트 구성
    system = build_system_prompt(hits, scene=scene, difficulty=difficulty)
    _HISTORY[session_id].append({"role": "user", "content": message})

    # 3) LLM 호출
    reply = _call_llm(system, list(_HISTORY[session_id]))
    _HISTORY[session_id].append({"role": "assistant", "content": reply})

    return {
        "reply": reply,
        "sources": [
            {"type": h["metadata"]["type"], "place": h["metadata"]["place"], "score": h["score"]}
            for h in hits
        ],
        "ended": False,
    }
