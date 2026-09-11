import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
# from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

@pytest.fixture()
def db_session_test():

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
        )
    Base.metadata.create_all(bind=engine)

    sessiontest = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    session = sessiontest()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)