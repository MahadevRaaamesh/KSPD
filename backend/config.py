from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/kspd.db"
    QUICKML_LLM_ENDPOINT: str = ""
    QUICKML_OAUTH_TOKEN: str = ""
    QUICKML_ORG_ID: str = ""
    FAISS_INDEX_PATH: str = "./data/fir_index.faiss"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
