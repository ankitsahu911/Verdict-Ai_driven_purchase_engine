import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://verdict:verdict@localhost:5432/verdict",
)

class Base(DeclarativeBase):
    pass


def _init_engine():
    global DATABASE_URL
    if DATABASE_URL.startswith("sqlite"):
        eng = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=eng)
        return eng

    try:
        eng = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
        with eng.connect():
            return eng
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        sqlite_file = data_dir / "verdict_dev.db"
        logger.warning(
            "PostgreSQL unreachable (%s); using local SQLite fallback at %s",
            e,
            sqlite_file,
        )
        sqlite_url = f"sqlite:///{sqlite_file}"
        DATABASE_URL = sqlite_url
        sqlite_eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=sqlite_eng)
        return sqlite_eng


engine = _init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
