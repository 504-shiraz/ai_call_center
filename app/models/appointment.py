from datetime import date, time, datetime
from typing import Optional

from sqlalchemy import String, Date, Time, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

class Appointment(Base):
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    
    customer_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    
    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )
    
    appointment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    appointment_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="confirmed",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )