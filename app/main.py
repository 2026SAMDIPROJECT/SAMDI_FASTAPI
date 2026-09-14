"""SAMDI - 진상 캐릭터 챗봇 API."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.chat import engine
from app.config import settings
from app.rag.store import build_index, get_collection, search
from app.schemas import ChatRequest, ChatResponse

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="SAMDI 진상 챗봇 API",
    description="RAG 기반 진상 손님 캐릭터와 대화하는 API",
    version="0.1.0",
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    page = STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "SAMDI 진상 챗봇 API. /docs 로 이동하세요."}


@app.get("/health")
def health():
    try:
        count = get_collection().count()
    except Exception as e:  # 인덱스가 아직 없을 수 있다
        return {"status": "degraded", "indexed": 0, "detail": str(e)}
    return {
        "status": "ok" if count else "empty-index",
        "indexed": count,
        "llm_provider": settings.llm_provider,
        "chat_model": settings.chat_model,
    }


@app.post("/admin/reindex")
def reindex():
    """데이터 파일을 다시 읽어 인덱스를 재구축한다."""
    try:
        n = build_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인덱싱 실패: {e}") from e
    return {"indexed": n}


@app.get("/search")
def search_cases(q: str, k: int = 3):
    """RAG 검색만 따로 확인하는 디버그용 엔드포인트."""
    return {"query": q, "hits": search(q, k)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = engine.chat(
            session_id=req.session_id,
            message=req.message,
            scene=req.scene,
            difficulty=req.difficulty,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대화 생성 실패: {e}") from e
    return result


@app.post("/chat/reset")
def reset(session_id: str = "default"):
    engine.reset(session_id)
    return {"session_id": session_id, "reset": True}
