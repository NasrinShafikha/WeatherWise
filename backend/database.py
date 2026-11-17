from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to the SQLite database
DATABASE_URL = "sqlite:///./weatherwise.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# Base class for database models
Base = declarative_base()


# Get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
