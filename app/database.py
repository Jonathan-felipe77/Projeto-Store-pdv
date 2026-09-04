from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

# Carrega o arquivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception(
        "DATABASE_URL não encontrada. Verifique o arquivo .env"
    )

# SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=True
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=True
    )

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()