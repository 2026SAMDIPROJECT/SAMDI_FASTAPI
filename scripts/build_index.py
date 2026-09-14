"""인덱스 빌드 스크립트.  실행:  python scripts/build_index.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.rag.store import build_index  # noqa: E402

if __name__ == "__main__":
    n = build_index()
    print(f"[OK] {n}건 적재 완료 -> {settings.chroma_dir} / {settings.collection_name}")
