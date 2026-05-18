from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Field, SQLModel, Session, create_engine

DATABASE_PATH = Path(__file__).resolve().parents[2] / "storage" / "app.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DATABASE_PATH}")


class Job(SQLModel, table=True):
    id: str = Field(primary_key=True)
    filename: str
    status: str = "processing"
    language: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)