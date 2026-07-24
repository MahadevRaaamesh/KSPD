import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Float, ForeignKey, Boolean
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
metadata = MetaData()

# Define Tables matching Karnataka Police DB Schema

case_master = Table(
    "CaseMaster",
    metadata,
    Column("CaseMasterID", Integer, primary_key=True, autoincrement=True),
    Column("CrimeNo", String),
    Column("CaseNo", String),
    Column("CrimeRegisteredDate", String),  # SQLite doesn't have strict DATE
    Column("PolicePersonID", Integer, nullable=True),
    Column("PoliceStationID", Integer, nullable=True),
    Column("CaseCategoryID", Integer, nullable=True),
    Column("GravityOffenceID", Integer, nullable=True),
    Column("CrimeMajorHeadID", Integer, nullable=True),
    Column("CrimeMinorHeadID", Integer, nullable=True),
    Column("CaseStatusID", Integer, nullable=True),
    Column("CourtID", Integer, nullable=True),
    Column("IncidentFromDate", String, nullable=True),
    Column("IncidentToDate", String, nullable=True),
    Column("latitude", Float, nullable=True),
    Column("longitude", Float, nullable=True),
    Column("BriefFacts", Text, nullable=True),
)

accused = Table(
    "Accused",
    metadata,
    Column("AccusedMasterID", Integer, primary_key=True, autoincrement=True),
    Column("CaseMasterID", Integer, ForeignKey("CaseMaster.CaseMasterID")),
    Column("AccusedName", String),
    Column("AgeYear", Integer, nullable=True),
    Column("GenderID", Integer, nullable=True),
    Column("PersonID", String, nullable=True),
)

victim = Table(
    "Victim",
    metadata,
    Column("VictimMasterID", Integer, primary_key=True, autoincrement=True),
    Column("CaseMasterID", Integer, ForeignKey("CaseMaster.CaseMasterID")),
    Column("VictimName", String),
    Column("AgeYear", Integer, nullable=True),
    Column("GenderID", Integer, nullable=True),
    Column("VictimPolice", String, nullable=True),
)

unit = Table(
    "Unit",  # Represents Police Station
    metadata,
    Column("UnitID", Integer, primary_key=True, autoincrement=True),
    Column("UnitName", String),
    Column("DistrictID", Integer, nullable=True),
    Column("StateID", Integer, nullable=True),
)

district = Table(
    "District",
    metadata,
    Column("DistrictID", Integer, primary_key=True, autoincrement=True),
    Column("DistrictName", String),
)

act_section_association = Table(
    "ActSectionAssociation",
    metadata,
    Column("CaseMasterID", Integer, ForeignKey("CaseMaster.CaseMasterID")),
    Column("ActID", Integer),
    Column("SectionID", Integer),
)

act = Table(
    "Act",
    metadata,
    Column("ActCode", String, primary_key=True),
    Column("ActDescription", String, nullable=True),
    Column("ShortName", String, nullable=True),
)

section = Table(
    "Section",
    metadata,
    Column("SectionCode", String, primary_key=True),
    Column("SectionDescription", String, nullable=True),
    Column("ActCode", String, nullable=True),
)

crime_head = Table(
    "CrimeHead",
    metadata,
    Column("CrimeHeadID", Integer, primary_key=True, autoincrement=True),
    Column("CrimeGroupName", String),
)

crime_sub_head = Table(
    "CrimeSubHead",
    metadata,
    Column("CrimeSubHeadID", Integer, primary_key=True, autoincrement=True),
    Column("CrimeHeadID", Integer, nullable=True),
    Column("CrimeHeadName", String, nullable=True),
)

case_status_master = Table(
    "CaseStatusMaster",
    metadata,
    Column("CaseStatusID", Integer, primary_key=True),
    Column("CaseStatusName", String),
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def execute_query(query: str, params: dict = {}) -> list[dict]:
    from sqlalchemy import text
    async with engine.connect() as conn:
        result = await conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

async def execute_insert(table_name: str, data: dict) -> int:
    from sqlalchemy import text
    keys = ", ".join(data.keys())
    placeholders = ", ".join([f":{k}" for k in data.keys()])
    query = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})"
    
    async with engine.begin() as conn:
        result = await conn.execute(text(query), data)
        return result.lastrowid

async def execute_count(query: str, params: dict = {}) -> int:
    from sqlalchemy import text
    async with engine.connect() as conn:
        result = await conn.execute(text(query), params)
        return result.scalar()
