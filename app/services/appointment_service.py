from datetime import date as Date
from datetime import time as Time
from datetime import datetime
import logging
import time

from app.database.connection import get_session
from app.repositories.appointment_repository import AppointmentRepository

logger = logging.getLogger(__name__)

class AppointmentService:
    BUSINESS_START = Time(9,0)
    BUSINESS_END = Time(17,0)
    
    def __init__(self):
        self.repository = AppointmentRepository()
        
    def _parse_date(self, value:str) -> Date:
        try:
            return Date.fromisoformat(value)
        except ValueError:
            raise ValueError(
                "Invalid Appointment Date. Use YYYY-MM-DD."
            )
            
    def _parse_time(self, value:str) -> Time:
        try:
            return Time.fromisoformat(value)
        except ValueError:
            raise ValueError(
                "Invalid Appointment Time. Use HH:MM."
            )
            
    def _validate_slot(
        self,
        appointment_date: Date,
        appointment_time: Time,
    ):
        today = datetime.now().date()
        
        if appointment_date < today:
            raise ValueError(
                "Appointment Date Cannot be in the Past."
            )
            
        if not (
            self.BUSINESS_START
            <= appointment_time
            < self.BUSINESS_END
        ):
            raise ValueError(
                "Appointments are available between 09:00 and 17:00."
            )
            
        if appointment_time.minute not in (0, 30):
            raise ValueError(
                "Appointment are available on 30-minutes Intervals."
            )
            
    def check_availability(
        self,
        appointment_date: str,
        appointment_time: str,
    ) -> dict:
        
        started_at = time.perf_counter()
        logger.info("Checking appointment availability date=%s time=%s", appointment_date, appointment_time)
        parsed_date = self._parse_date(appointment_date)
        parsed_time = self._parse_time(appointment_time)
        
        self._validate_slot(
            parsed_date, parsed_time
        )
        
        with get_session() as session:
            
            existing = self.repository.get_active_by_slot(
                session,
                parsed_date,
                parsed_time
            )
            
        if existing:
            logger.info("Appointment slot unavailable date=%s time=%s elapsed_ms=%.0f", appointment_date, appointment_time, (time.perf_counter() - started_at) * 1000)
            return {
                "success" : True,
                "available" : False,
                "date" : appointment_date,
                "time" : appointment_time,
                "message" : (
                    "This Appointment Slot is Already Booked!!."
                ),
            }
            
        result = {
            "success" : True,
            "available" : True,
            "date" : appointment_date,
            "time" : appointment_time,
            "message" : (
                "This Appointment Slot is Available!!"
            ),
        }
        logger.info("Appointment slot available date=%s time=%s elapsed_ms=%.0f", appointment_date, appointment_time, (time.perf_counter() - started_at) * 1000)
        return result
        
    def book_appointment(
        self,
        customer_name: str,
        customer_phone: str | None,
        appointment_date: str,
        appointment_time: str,
    ) -> dict:
        
        if not customer_name.strip():
            return {
                "success" : False,
                "error" : "Customer Name is Required!!."
            }
            
        started_at = time.perf_counter()
        logger.info("Booking appointment name=%s date=%s time=%s", customer_name, appointment_date, appointment_time)
        parsed_date = self._parse_date(appointment_date)
        parsed_time = self._parse_time(appointment_time)
        
        self._validate_slot(
            parsed_date, parsed_time
        )
        
        with get_session() as session:
            
            existing = self.repository.get_active_by_slot(
                session,
                parsed_date,
                parsed_time, 
            )
            
            if existing:
                
                result = {
                    "success" : False,
                    "booked" : False,
                    "date" : appointment_date,
                    "time" : appointment_time,
                    "message" : (
                        "The Slot is No Longer Available!!."
                    ),
                }
                logger.info("Appointment slot already booked date=%s time=%s elapsed_ms=%.0f", appointment_date, appointment_time, (time.perf_counter() - started_at) * 1000)
                return result
                
            appointment = self.repository.create(
                session=session,
                customer_name = customer_name.strip(),
                customer_phone = customer_phone,
                appointment_date = parsed_date,
                appointment_time = parsed_time
            )
            
            session.commit()
            
            result = {
                "success": True,
                "booked": True,
                "appointment_id" : (
                    f"APT-{appointment.id:06d}"
                ),
                "customer_name": appointment.customer_name,
                "date" : appointment_date,
                "time" : appointment_time,
                "message" : (
                    "Appointment Successfully Booked!!"
                ) 
            }
            logger.info("Appointment booked id=%s date=%s time=%s elapsed_ms=%.0f", result["appointment_id"], appointment_date, appointment_time, (time.perf_counter() - started_at) * 1000)
            return result
        