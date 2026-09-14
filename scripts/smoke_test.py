"""API 키 없이 RAG 파이프라인과 API 라우팅을 검증한다.

임베딩과 LLM 호출을 가짜 함수로 갈아끼우기 때문에 비용이 들지 않는다.
검색 '품질'이 아니라 '연결'을 확인하는 테스트다.

실행:  python scripts/smoke_test.py
"""
import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["CHROMA_DIR"] = tempfile.mkdtemp()
os.environ["DATA_PATH"] = str(ROOT / "data" / "jinsang_cases.jsonl")

from app.chat import engine, persona  # noqa: E402
from app.rag import store  # noqa: E402

DIM = 256


def fake_embed(texts):
    """문자 bigram 해시 기반 가짜 임베딩 (의미 검색은 못 하지만 파이프라인 검증엔 충분)."""
    out = []
    for t in texts:
        v = [0.0] * DIM
        for i in range(len(t) - 1):
            idx = int(hashlib.md5(t[i : i + 2].encode()).hexdigest(), 16) % DIM
            v[idx] += 1.0
        norm = sum(x * x for x in v) ** 0.5 or 1.0
        out.append([x / norm for x in v])
    return out


def main() -> None:
    store.embed = fake_embed

    n = store.build_index()
    assert n > 0
    print(f"[1] 인덱싱 {n}건 OK")

    hits = store.search("음료 다 마셨는데 환불해 달라고 우기는 손님", k=3)
    assert hits and all({"document", "metadata", "score"} <= set(h) for h in hits)
    print("[2] 검색 OK:", [(h["metadata"]["type"], h["score"]) for h in hits])

    prompt = persona.build_system_prompt(hits, scene="카페", difficulty="hard")
    for kw in ("진상 손님", "카페", "절대 금지"):
        assert kw in prompt, kw
    assert "(참고 사례 없음" in persona.build_system_prompt([], scene="카페")
    print(f"[3] 시스템 프롬프트 OK ({len(prompt)}자)")

    calls = []

    def fake_llm(system, messages):
        calls.append((system, list(messages)))
        return "아니 이게 말이 돼요? 사장 불러요."

    engine._call_llm = fake_llm

    engine.chat("s1", "고객님, 어떤 점이 불편하셨을까요?", scene="카페")
    engine.chat("s1", "환불 규정상 개봉 후에는 어렵습니다.", scene="카페")
    assert [m["role"] for m in calls[-1][1]] == ["user", "assistant", "user"]
    print("[4] 멀티턴 히스토리 OK")

    assert engine.chat("s1", "그만")["ended"] and engine.history("s1") == []
    print("[5] 종료 키워드 OK")

    from fastapi.testclient import TestClient  # noqa: E402

    from app import main as api  # noqa: E402

    api.engine._call_llm = fake_llm
    api.search = store.search
    client = TestClient(api.app)

    assert client.get("/health").json()["indexed"] == n
    assert len(client.get("/search", params={"q": "별점 협박", "k": 2}).json()["hits"]) == 2
    assert client.post("/chat", json={"session_id": "api", "message": "확인해 드릴게요."}).status_code == 200
    assert client.post("/chat", json={"session_id": "api", "message": ""}).status_code == 422
    assert client.post("/chat", json={"session_id": "api", "message": "hi", "difficulty": "insane"}).status_code == 422
    assert client.post("/chat/reset", params={"session_id": "api"}).json()["reset"] is True
    print("[6] API 엔드포인트 + 입력 검증 OK")

    print("\n=== 전체 통과 ===")


if __name__ == "__main__":
    main()
