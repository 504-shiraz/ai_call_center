import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{DATA_DIR / 'appointments.db'}"
)

class Base(DeclarativeBase):
    pass

connect_args = {}

if DATABASE_URL.startswith('sqlite'):
    connect_args = {
        "check_same_thread": False
    }
    
engine = create_engine (
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

def init_db():
    # Import Models Before create_all()
    from app.models.appointment import Appointment
    
    Base.metadata.create_all(bind=engine)
    
    
def get_session():
    return SessionLocal()

