"""환경변수 기반 설정. .env 파일에서 읽어온다."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str) -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default


@dataclass
class Settings:
    # LLM: openai | anthropic
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "openai"))
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "gpt-4o-mini"))

    # 임베딩: openai | local(sentence-transformers)
    embed_provider: str = field(default_factory=lambda: _env("EMBED_PROVIDER", "openai"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "text-embedding-3-small"))

    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY", ""))

    # 벡터 DB
    chroma_dir: str = field(default_factory=lambda: _env("CHROMA_DIR", "./.chroma"))
    collection_name: str = field(default_factory=lambda: _env("COLLECTION_NAME", "jinsang"))
    data_path: str = field(default_factory=lambda: _env("DATA_PATH", "./data/jinsang_cases.jsonl"))

    # RAG 파라미터
    top_k: int = field(default_factory=lambda: int(_env("TOP_K", "3")))
    max_history: int = field(default_factory=lambda: int(_env("MAX_HISTORY", "12")))
    max_tokens: int = field(default_factory=lambda: int(_env("MAX_TOKENS", "300")))
    temperature: float = field(default_factory=lambda: float(_env("TEMPERATURE", "0.9")))


settings = Settings()
