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

    def get_active_by_id_and_phone(
        self,
        session: Session,
        appointment_id: int,
        customer_phone: str,
    ) -> Appointment | None:
        statement = (
            select(Appointment)
            .where(
                Appointment.id == appointment_id,
                Appointment.customer_phone == customer_phone,
                Appointment.status == "confirmed",
            )
        )
        return session.execute(statement).scalar_one_or_none()

    def get_active_by_id_and_identity(
        self,
        session: Session,
        appointment_id: int,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        customer_email: str | None = None,
    ) -> Appointment | None:
        conditions = [
            Appointment.id == appointment_id,
            Appointment.status == "confirmed",
        ]
        if customer_name:
            conditions.append(Appointment.customer_name == customer_name)
        if customer_phone:
            conditions.append(Appointment.customer_phone == customer_phone)
        if customer_email:
            conditions.append(Appointment.customer_email == customer_email)
        return session.execute(select(Appointment).where(*conditions)).scalar_one_or_none()

    def get_active_by_phone(
        self,
        session: Session,
        customer_phone: str,
    ) -> list[Appointment]:
        statement = (
            select(Appointment)
            .where(
                Appointment.customer_phone == customer_phone,
                Appointment.status == "confirmed",
            )
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        )
        return list(session.execute(statement).scalars())

    def get_active_by_identity(
        self,
        session: Session,
        customer_name: str | None = None,
        customer_phone: str | None = None,
        customer_email: str | None = None,
    ) -> list[Appointment]:
        conditions = [Appointment.status == "confirmed"]
        if customer_name:
            conditions.append(Appointment.customer_name == customer_name)
        if customer_phone:
            conditions.append(Appointment.customer_phone == customer_phone)
        if customer_email:
            conditions.append(Appointment.customer_email == customer_email)

        statement = (
            select(Appointment)
            .where(*conditions)
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        )
        return list(session.execute(statement).scalars())
    
    def create(
        self,
        session: Session,
        customer_name: str,
        customer_phone: str | None,
        customer_email: str | None,
        appointment_date: date,
        appointment_time: time,
    ) -> Appointment :
        
        appointment = Appointment(
            customer_name = customer_name,
            customer_phone = customer_phone,
            customer_email = customer_email,
            appointment_date = appointment_date,
            appointment_time = appointment_time,
            status = "confirmed",
        )
        
        session.add(appointment)
        session.flush()
        
        return appointment

    def get_available_slots(
        self,
        session: Session,
        appointment_date: date,
        appointment_times: list[time],
    ) -> list[time]:
        statement = (
            select(Appointment.appointment_time)
            .where(
                Appointment.appointment_date == appointment_date,
                Appointment.appointment_time.in_(appointment_times),
                Appointment.status == "confirmed",
            )
        )
        booked_times = set(session.execute(statement).scalars())
        return [appointment_time for appointment_time in appointment_times if appointment_time not in booked_times]