from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment

class AppointmentRepository():
    
    def get_active_by_slot(
        self,
        session: Session,
        appointment_date: date,
        appointment_time: time,
    ) -> Appointment | None :
        
        statement = (
            select(Appointment).
            where(
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time == appointment_time,
                Appointment.status == "confirmed"
            )
        )
        
        return session.execute(statement).scalar_one_or_none()
    
    def create(
        self,
        session: Session,
        customer_name: str,
        customer_phone: str | None,
        appointment_date: date,
        appointment_time: time,
    ) -> Appointment :
        
        appointment = Appointment(
            customer_name = customer_name,
            customer_phone = customer_phone,
            appointment_date = appointment_date,
            appointment_time = appointment_time,
            status = "confirmed",
        )
        
        session.add(appointment)
        session.flush()
        
        return appointment