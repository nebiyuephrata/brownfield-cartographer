from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _default_db_url() -> str:
    # Store DB in .cartography by default.
    return "sqlite:///./.cartography/cartography.db"


DB_URL = os.getenv("CARTOGRAPHY_DB_URL", _default_db_url())


def _ensure_sqlite_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    path = url.replace("sqlite:///", "", 1)
    db_path = Path(path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    run_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    repo_path = Column(String, nullable=False)
    output_dir = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(String, nullable=True)


_ensure_sqlite_dir(DB_URL)
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
