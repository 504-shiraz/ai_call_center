import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
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

    print(f"[DB] Database URL: {DATABASE_URL}")

    if DATABASE_URL.startswith("sqlite"):
        columns = {
            column["name"]
            for column in inspect(engine).get_columns("appointments")
        }
        if "customer_email" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE appointments "
                        "ADD COLUMN customer_email VARCHAR(254)"
                    )
                )
            columns.add("customer_email")
        print(f"[DB] Appointments columns: {', '.join(sorted(columns))}")
    
    
def get_session():
    return SessionLocal()

