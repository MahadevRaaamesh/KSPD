from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Backend package directory — all relative paths resolve against this so the
# app and scripts work no matter which directory they are launched from.
BASE_DIR = Path(__file__).resolve().parent

_SQLITE_PREFIXES = ("sqlite+aiosqlite:///", "sqlite:///")


def _absolutize_sqlite_url(url: str) -> str:
    """Make the file path inside a sqlite URL absolute (relative to BASE_DIR)."""
    for prefix in _SQLITE_PREFIXES:
        if url.startswith(prefix):
            raw_path = url[len(prefix):]
            path = Path(raw_path)
            if not path.is_absolute():
                path = (BASE_DIR / raw_path).resolve()
            return prefix + path.as_posix()
    return url


class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/mock_data/mock_fir_data.db"
    QUICKML_LLM_ENDPOINT: str = ""
    QUICKML_OAUTH_TOKEN: str = ""
    QUICKML_ORG_ID: str = ""
    FAISS_INDEX_PATH: str = "./data/fir_index.faiss"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CORS_ORIGINS: list[str] = ["*"]

    @field_validator("DATABASE_URL")
    @classmethod
    def _resolve_database_url(cls, v: str) -> str:
        return _absolutize_sqlite_url(v)

    @field_validator("FAISS_INDEX_PATH")
    @classmethod
    def _resolve_faiss_path(cls, v: str) -> str:
        path = Path(v)
        if not path.is_absolute():
            path = (BASE_DIR / v).resolve()
        return path.as_posix()

    class Config:
        env_file = str(BASE_DIR / ".env")


settings = Settings()
