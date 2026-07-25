from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def execute_query(query: str, params: dict = {}) -> list[dict]:
    async with engine.connect() as conn:
        result = await conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


async def execute_insert(table_name: str, data: dict) -> int:
    keys = ", ".join(data.keys())
    placeholders = ", ".join([f":{k}" for k in data.keys()])
    query = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})"

    async with engine.begin() as conn:
        result = await conn.execute(text(query), data)
        return result.lastrowid


async def execute_count(query: str, params: dict = {}) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(text(query), params)
        return result.scalar()
