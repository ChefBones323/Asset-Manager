import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def serializable_session():
    from sqlalchemy.orm import Session
    return Session(bind=engine, autocommit=False, autoflush=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
