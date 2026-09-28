from datetime import date as Date
from datetime import time as Time
from datetime import datetime
import time
import re
import logging
from datetime import timedelta
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_session
from app.repositories.appointment_repository import AppointmentRepository

logger = logging.getLogger(__name__)

class AppointmentService:
    BUSINESS_START = Time(9,0)
    BUSINESS_END = Time(17,0)
    
    def __init__(self):
        self.repository = AppointmentRepository()
        
    def _parse_date(self, value:str) -> Date:
        value = value.strip()
        try:
            return Date.fromisoformat(value)
        except ValueError:
            for date_format in (
                "%B %d, %Y",
                "%b %d, %Y",
                "%d %B %Y",
                "%d %b %Y",
            ):
                try:
                    return datetime.strptime(value, date_format).date()
                except ValueError:
                    continue
        raise ValueError("Invalid Appointment Date. Use a clear date such as September 24, 2026.")
            
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
                "I cannot book past dates. I can only book future dates."
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
        
        logger.info("checking availability date=%s time=%s", appointment_date, appointment_time)
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
            logger.info("slot unavailable date=%s time=%s", appointment_date, appointment_time)
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
        logger.info("slot available date=%s time=%s", appointment_date, appointment_time)
        return result

    def find_alternative_slots(
        self,
        appointment_date: str,
        appointment_time: str,
        radius: int = 2,
    ) -> dict:
        parsed_date = self._parse_date(appointment_date)
        requested_time = self._parse_time(appointment_time)
        self._validate_slot(parsed_date, requested_time)
        candidate_times = []
        for offset in range(-radius, radius + 1):
            candidate = (
                datetime.combine(parsed_date, requested_time)
                + timedelta(minutes=30 * offset)
            ).time()
            if self.BUSINESS_START <= candidate < self.BUSINESS_END:
                candidate_times.append(candidate)

        with get_session() as session:
            available = self.repository.get_available_slots(
                session,
                parsed_date,
                candidate_times,
            )

        return {
            "success": True,
            "date": appointment_date,
            "requested_time": appointment_time,
            "slots": [slot.strftime("%H:%M") for slot in available],
        }
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        phone = re.sub(r"[\s\-\(\)]", "", phone)
        
        if phone.startswith("03") and len(phone) == 11:
            phone = "+92" + phone[1:]
        elif phone.startswith("92") and len(phone) ==  12:
            phone = "+" + phone
        
        return phone
    
    def is_valid_phone(self, phone:str) -> bool:
        normalized = self.normalize_phone(phone)
        return bool(re.fullmatch(r"\+92\d{10}", normalized))

    @staticmethod
    def is_valid_email(email: str) -> bool:
        value = email.strip()
        local, separator, domain = value.partition("@")
        return bool(
            separator
            and local
            and domain
            and "." in domain
            and not re.search(r"\s", value)
        )

    def _normalize_identity(
        self,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
        require_secure_contact: bool = False,
    ) -> tuple[str | None, str | None, str | None]:
        normalized_name = customer_name.strip() or None
        normalized_phone = self.normalize_phone(customer_phone) if customer_phone.strip() else None
        normalized_email = customer_email.strip().lower() or None

        if normalized_phone and not self.is_valid_phone(normalized_phone):
            raise ValueError("Invalid Phone Number!!.")
        if normalized_email and not self.is_valid_email(normalized_email):
            raise ValueError("Invalid Customer Email Address!!.")
        if not any((normalized_name, normalized_phone, normalized_email)):
            raise ValueError("Provide your name, phone number, or email address.")
        if require_secure_contact and not (normalized_phone or normalized_email):
            raise ValueError("For security, provide your phone number or email address.")
        return normalized_name, normalized_phone, normalized_email

    @staticmethod
    def _spoken_phone(phone: str) -> str:
        digit_words = {
            "0": "zero", "1": "one", "2": "two", "3": "three",
            "4": "four", "5": "five", "6": "six", "7": "seven",
            "8": "eight", "9": "nine",
        }
        digits = "".join(digit for digit in phone if digit.isdigit())
        if digits.startswith("92") and len(digits) == 12:
            digits = "0" + digits[2:]
        groups = (digits[:4], digits[4:7], digits[7:])
        return ", ".join(
            " ".join(digit_words[digit] for digit in group)
            for group in groups
            if group
        )

    @staticmethod
    def _spoken_time(value: Time) -> str:
        number_words = {
            1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
            11: "eleven", 12: "twelve", 30: "thirty",
        }
        hour = value.hour % 12 or 12
        minute = value.minute
        suffix = "AM" if value.hour < 12 else "PM"
        if minute == 0:
            return f"{number_words[hour]} {suffix}"
        return f"{number_words[hour]} {number_words.get(minute, str(minute))} {suffix}"
        
    def book_appointment(
        self,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        appointment_date: str,
        appointment_time: str,
    ) -> dict:
        
        if not customer_name.strip():
            return {
                "success" : False,
                "error" : "Customer Name is Required!!."
            }
            
        customer_phone = self.normalize_phone(customer_phone)
            
        if not customer_phone.strip():
            return {
                "success" : False,
                "booked" : False,
                "error" : "Customer Phone is Required!!."
            }

        if not self.is_valid_phone(customer_phone):
            return {
                "success" : False,
                "booked" : False,
                "error" : "Invalid Phone Number!!."
            }

        customer_email = customer_email.strip().lower()
        if not customer_email:
            return {
                "success": False,
                "booked": False,
                "error": "Customer Email is Required!!.",
            }
        if not self.is_valid_email(customer_email):
            return {
                "success": False,
                "booked": False,
                "error": "Invalid Customer Email!!.",
            }
            
        logger.info("booking appointment name=%s date=%s time=%s", customer_name, appointment_date, appointment_time)
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
                logger.warning("booking rejected because slot is already booked date=%s time=%s", appointment_date, appointment_time)
                return result
                
            try:
                appointment = self.repository.create(
                    session=session,
                    customer_name=customer_name.strip(),
                    customer_phone=customer_phone,
                    customer_email=customer_email,
                    appointment_date=parsed_date,
                    appointment_time=parsed_time,
                )
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.warning("booking rejected because slot was taken concurrently date=%s time=%s", appointment_date, appointment_time)
                return {
                    "success": False,
                    "booked": False,
                    "date": appointment_date,
                    "time": appointment_time,
                    "message": "The Slot is No Longer Available!!.",
                }
            
            result = {
                "success": True,
                "booked": True,
                "appointment_id" : (
                    f"APT-{appointment.id:06d}"
                ),
                "customer_name": appointment.customer_name,
                "customer_email": appointment.customer_email,
                "phone_spoken": self._spoken_phone(appointment.customer_phone),
                "time_spoken": self._spoken_time(appointment.appointment_time),
                "date" : appointment_date,
                "time" : appointment_time,
                "message" : (
                    "Appointment Successfully Booked!!"
                ) 
            }
            logger.info("appointment booked id=%s", result["appointment_id"])
            return result

    def _normalize_and_validate_phone(self, customer_phone: str) -> str:
        normalized_phone = self.normalize_phone(customer_phone)
        if not normalized_phone.strip():
            raise ValueError("Customer Phone is Required!!.")
        if not self.is_valid_phone(normalized_phone):
            raise ValueError("Invalid Phone Number!!.")
        return normalized_phone

    @staticmethod
    def _parse_appointment_id(appointment_id: str) -> int:
        match = re.fullmatch(r"APT-(\d+)", appointment_id.strip().upper())
        if not match:
            raise ValueError("Invalid appointment ID.")
        return int(match.group(1))

    def get_my_appointments(
        self,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
    ) -> dict:
        normalized_name, normalized_phone, normalized_email = self._normalize_identity(
            customer_name, customer_phone, customer_email,
        )
        with get_session() as session:
            appointments = self.repository.get_active_by_identity(
                session, normalized_name, normalized_phone, normalized_email,
            )

        return {
            "success": True,
            "appointments": [
                {
                    "appointment_id": f"APT-{appointment.id:06d}",
                    "customer_name": appointment.customer_name,
                    "phone": appointment.customer_phone,
                    "email": appointment.customer_email,
                    "date": appointment.appointment_date.isoformat(),
                    "time": appointment.appointment_time.strftime("%H:%M"),
                    "phone_spoken": self._spoken_phone(appointment.customer_phone),
                    "time_spoken": self._spoken_time(appointment.appointment_time),
                    "status": appointment.status,
                }
                for appointment in appointments
            ],
        }

    def cancel_appointment(
        self,
        appointment_id: str,
        customer_phone: str = "",
        customer_email: str = "",
        customer_name: str = "",
    ) -> dict:
        numeric_id = self._parse_appointment_id(appointment_id)
        normalized_name, normalized_phone, normalized_email = self._normalize_identity(
            customer_name, customer_phone, customer_email, require_secure_contact=True,
        )
        with get_session() as session:
            appointment = self.repository.get_active_by_id_and_identity(
                session, numeric_id, normalized_name, normalized_phone, normalized_email,
            )
            if appointment is None:
                return {
                    "success": False,
                    "cancelled": False,
                    "error": "Appointment was not found or is already cancelled.",
                }
            appointment.status = "cancelled"
            session.commit()

        logger.info("appointment cancelled id=%s", appointment_id)
        return {
            "success": True,
            "cancelled": True,
            "appointment_id": appointment_id,
            "message": "Appointment cancelled successfully.",
        }

    def reschedule_appointment(
        self,
        appointment_id: str,
        new_date: str,
        new_time: str,
        customer_phone: str = "",
        customer_email: str = "",
        customer_name: str = "",
    ) -> dict:
        numeric_id = self._parse_appointment_id(appointment_id)
        normalized_name, normalized_phone, normalized_email = self._normalize_identity(
            customer_name, customer_phone, customer_email, require_secure_contact=True,
        )
        parsed_date = self._parse_date(new_date)
        parsed_time = self._parse_time(new_time)
        self._validate_slot(parsed_date, parsed_time)

        with get_session() as session:
            appointment = self.repository.get_active_by_id_and_identity(
                session, numeric_id, normalized_name, normalized_phone, normalized_email,
            )
            if appointment is None:
                return {
                    "success": False,
                    "rescheduled": False,
                    "error": "Appointment was not found or is already cancelled.",
                }
            existing = self.repository.get_active_by_slot(
                session,
                parsed_date,
                parsed_time,
            )
            if existing is not None and existing.id != numeric_id:
                return {
                    "success": False,
                    "rescheduled": False,
                    "error": "The new appointment slot is unavailable.",
                }
            appointment.appointment_date = parsed_date
            appointment.appointment_time = parsed_time
            session.commit()

        logger.info("appointment rescheduled id=%s date=%s time=%s", appointment_id, new_date, new_time)
        return {
            "success": True,
            "rescheduled": True,
            "appointment_id": appointment_id,
            "date": new_date,
            "time": new_time,
            "message": "Appointment rescheduled successfully.",
        }
        