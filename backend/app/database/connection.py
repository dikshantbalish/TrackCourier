from collections.abc import Generator

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

database_url = settings.sqlalchemy_database_url
parsed_database_url: URL = make_url(database_url)
engine_options: dict[str, object] = {"pool_pre_ping": True}

if parsed_database_url.get_backend_name() == "sqlite":
    engine_options["connect_args"] = {"check_same_thread": False}
    if parsed_database_url.database in {None, "", ":memory:"}:
        engine_options["poolclass"] = StaticPool

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


if parsed_database_url.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
