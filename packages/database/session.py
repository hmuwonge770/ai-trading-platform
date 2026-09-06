from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.trading.config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency that closes a database session after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
