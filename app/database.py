from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

_settings = get_settings()

# SQLite abre arquivos locais: desabilita o pool de threads e permite
# que a mesma conexão seja compartilhada entre threads do FastAPI.
if _settings.database_url.startswith("sqlite"):
    _engine_args = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
else:
    _engine_args = {}

engine = create_engine(_settings.database_url, **_engine_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão por request, fechando-a ao final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
