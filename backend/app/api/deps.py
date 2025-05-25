from typing import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal


def get_db() -> Generator:
    """Dependency to get database session."""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
