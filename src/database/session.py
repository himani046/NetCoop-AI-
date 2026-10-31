"""Create a local SQLite engine with foreign key enforcement."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from .models import Base

def make_engine(db_path: str | Path | None = None) -> Engine:
    path = Path(db_path or os.environ.get("NETCOOP_DB_PATH", "data/netcoop.db")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path.resolve()}", future=True)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(engine)
    return engine

def session_factory(db_path: str | Path | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=make_engine(db_path), expire_on_commit=False)
