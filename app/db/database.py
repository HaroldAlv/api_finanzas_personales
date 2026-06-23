import os
from sqlmodel import create_engine, Session
from app.core.config import settings

# Ensure data directory exists based on configuration
db_path = settings.DATABASE_URL.replace("sqlite:///", "")

# Determine absolute path for the directory
db_dir = os.path.dirname(os.path.abspath(db_path))

if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, echo=True, connect_args=connect_args)

def get_session():
    with Session(engine) as session:
        yield session
