from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os

# Default local SQLite file path
DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), 
        "../../../../data/minepulse.db"
    )
)

# Ensure data directory exists
os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"timeout": 30}  # 30-second timeout to handle locked databases
)

# Enable SQLite foreign key constraints and WAL mode at connection check-in/creation
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency helper to manage database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database."""
    from backend.app.database.models import Base
    Base.metadata.create_all(bind=engine)
