import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from livekit.agents import Agent, RunContext, function_tool

from app.agent.prompt import build_system_prompt
from app.services.email_service import ConfirmationEmailService
from app.services.appointment_service import AppointmentService
from app.utils.performance import PerformanceTracker

logger = logging.getLogger(__name__)

@dataclass
class BookingState:
    appointment_date: str | None = None
    appointment_time: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    availability_checked: bool = False
    slot_available: bool = False
    confirmation_pending: bool = False
    confirmed_by_customer: bool = False
    booking_completed: bool = False
    appointment_id: str | None = None

    def reset(self) -> None:
        self.appointment_date = None
        self.appointment_time = None
        self.customer_name = None
        self.customer_phone = None
        self.customer_email = None
        self.availability_checked = False
        self.slot_available = False
        self.confirmation_pending = False
        self.confirmed_by_customer = False
        self.booking_completed = False
        self.appointment_id = None

# =================================================
# AI Agent
# =================================================

class AppointmentAgent(Agent):
    
    """
        CallCenterAgent is a specialized agent for handling call center interactions.
        It extends the base Agent class and can be customized with specific behaviors
        and capabilities relevant to call center operations.
    """
    
    def __init__(self):
        
        self.performance = PerformanceTracker()
        
        pakistan_now = datetime.now(ZoneInfo("Asia/Karachi"))
        current_date = pakistan_now.strftime("%Y-%m-%d")
        current_day = pakistan_now.strftime("%A")
        
        self.appointment_service = AppointmentService()
        self.email_service = ConfirmationEmailService()
        self.booking = BookingState()
        
        print()
        print("=" * 60)
        print("[AGENT] Initializing CallCenterAgent")
        print(f"[AGENT] Current Date : {current_date}")
        print(f"[AGENT] Current Day  : {current_day}")
        print("=" * 60)
        
        super().__init__(
            instructions=build_system_prompt( current_date=current_date, current_day=current_day ),
        )
        print()
        print("=" * 60)
        print("[TOOLS] Registered Agent Tools")
        print("=" * 60)

        for tool in self.tools:
            print(f"[TOOL REGISTERED] {tool.id}")
        print("=" * 60)

    def _tool_error(self, operation: str, error: Exception) -> dict:
        if isinstance(error, ValueError):
            logger.warning("%s rejected: %s", operation, error)
        else:
            logger.exception("%s Failed", operation)
        safe_message = str(error) if isinstance(error, ValueError) else (
            "I could not complete that request. Please try again."
        )
        return {
            "success": False,
            "error": safe_message,
            "message": safe_message,
        }

    def _remember_contact_from_history(self, context: RunContext) -> None:
        try:
            messages = context.session.history.messages
        except Exception:
            return

        for message in messages:
            if getattr(message, "role", None) != "user":
                continue
            content = getattr(message, "content", "")
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            content = str(content)
            email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", content)
            phone_match = re.search(r"(?:\+?92|0)\s*[\d\s()-]{9,}", content)
            name_match = re.search(
                r"(?im)^\s*([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\s*$",
                content,
            )
            self._remember_contact(
                name_match.group(1) if name_match else "",
                phone_match.group(0) if phone_match else "",
                email_match.group(0) if email_match else "",
            )

    def _remember_contact(
        self,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
    ) -> None:
        if customer_name.strip():
            self.booking.customer_name = customer_name.strip()
        if customer_phone.strip():
            normalized_phone = self.appointment_service.normalize_phone(customer_phone)
            if self.appointment_service.is_valid_phone(normalized_phone):
                self.booking.customer_phone = normalized_phone
        if customer_email.strip():
            normalized_email = customer_email.strip().lower()
            if self.appointment_service.is_valid_email(normalized_email):
                self.booking.customer_email = normalized_email

    def _validate_booking_contact(
        self, customer_name: str, customer_phone: str, customer_email: str,
    ) -> tuple[tuple[str, str, str] | None, dict | None]:
        
        if not customer_name.strip():
            return None, {
                "success": False,
                "booked": False,
                "error": "Customer Name is Required!!",
            }
        if not customer_phone.strip():
            return None, {
                "success": False,
                "booked": False,
                "error": "Customer Phone Number is Required!!",
            }
        if not customer_email.strip():
            return None, {
                "success": False,
                "booked": False,
                "error": "Customer Email is Required!!",
            }

        normalized_phone = self.appointment_service.normalize_phone(customer_phone)
        
        if not self.appointment_service.is_valid_phone(normalized_phone):
            return None, {
                "success": False,
                "booked": False,
                "error": "Invalid Phone Number!!",
            }

        normalized_email = customer_email.strip().lower()
        
        if not self.appointment_service.is_valid_email(normalized_email):
            return None, {
                "success": False,
                "booked": False,
                "error": "Invalid Customer Email Address!!",
            }
            
        return (customer_name.strip(), normalized_phone, normalized_email), None

    def _validate_booking_state(
        self, appointment_date: str, appointment_time: str, customer_confirmed: bool,
    ) -> dict | None:
        
        if not self.booking.slot_available:
            return {
                "success": False,
                "booked": False,
                "available": None,
                "error": (
                    "Availability has not been checked for this slot. "
                    "Do not tell the customer that the slot is unavailable. "
                    "Call check_availability first."
                ),
            }
        
        if (
            self.booking.appointment_date != appointment_date
            or self.booking.appointment_time != appointment_time
        ):
            return {
                "success": False,
                "booked": False,
                "error": "Appointment Details Changed. Availability must be Checked Again!!",
            }
        if not customer_confirmed:
            return {
                "success": False,
                "booked": False,
                "error": "Customer Confirmation is Required Before Booking.",
            }
        return None

    @function_tool()
    async def check_availability(
        self,
        context: RunContext,
        appointment_date: str,
        appointment_time: str,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
    ) -> dict:
            
        """
            Check real appointment availability in the appointment database for a specific date and time.

            MUST be called whenever the customer asks whether a specific appointment date and time is available.

            Never Guess or Invent Availability.
            
            appointment_date must be in YYYY-MM-DD format.
            appointment_time must be in HH:MM 24-hour format.
            
            This tool returns the REAL availability from the database. Never assume or invent availability
        """
        
        print()
        print("\n" + "=" * 60)
        print("[TOOL CALL] check_availability")
        print(f"[TOOL INPUT] date={appointment_date}")
        print(f"[TOOL INPUT] time={appointment_time}")
        print("[TOOL STATUS] Executing...")
        print("=" * 60)

        self._remember_contact_from_history(context)
        self._remember_contact(customer_name, customer_phone, customer_email)
        
        try:
            result = await asyncio.to_thread(
                self.appointment_service.check_availability,
                appointment_date, appointment_time,
            )
            
            print()
            print("[TOOL RESULT] check_availability")
            print(f"[TOOL OUTPUT] {result}")
            print(f"[TOOL SUCCESS] {result.get('success')}")
            print(f"[TOOL AVAILABLE] {result.get('available')}")
            print("=" * 60)
                
            if result.get("success") and result.get("available"):
                self.booking.appointment_date = appointment_date
                self.booking.appointment_time = appointment_time

                self.booking.availability_checked = True
                self.booking.slot_available = True

                self.booking.confirmation_pending = True
                self.booking.confirmed_by_customer = False
                
                print( "[BOOKING STATE] Available Slot stored as Pending!!")
            else:
                # Keep the requested slot so a follow-up such as "show me an
                # alternative" can call find_alternative_slots without asking again.
                self.booking.appointment_date = appointment_date
                self.booking.appointment_time = appointment_time
                self.booking.availability_checked = True
                self.booking.slot_available = False
                self.booking.confirmation_pending = False
                self.booking.confirmed_by_customer = False
                    
                print(f"[TOOL] Check Availabilty: {result}")
                
            return result

        except Exception as e:
            print("[TOOL ERROR] check_availability")
            print(f"[TOOL ERROR TYPE] {type(e).__name__}")
            print(f"[TOOL ERROR MESSAGE] {e}")
            print("=" * 60)

            self.booking.availability_checked = False
            self.booking.slot_available = False
            self.booking.confirmation_pending = False
            self.booking.confirmed_by_customer = False
                
            result = self._tool_error("check_availability", e)
            result["available"] = False
            return result
        
    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        appointment_date: str,
        appointment_time: str,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
        customer_confirmed: bool = False,
    ) -> dict:
            
        """
            Book an Real Appointment in the Appointment Database.

            MUST ONLY be call after:
            1. check_availability confirms the slot is available.
            2. the Customer Explicitly confirms they want to book it.
            3. the Customer's name is available.

            Never call this tool merely because the customer asked about availability.
            appointment_date must be YYYY-MM-DD.
            appointment_time must be HH:MM.
        """
        
        print()
        print("=" * 60)
        print("[TOOL CALL] book_appointment")
        print(f"[TOOL INPUT] customer_name={customer_name}")
        print(f"[TOOL INPUT] date={appointment_date}")
        print(f"[TOOL INPUT] time={appointment_time}")
        print(f"[TOOL INPUT] phone={customer_phone or '[not provided]'}")
        print("=" * 60)

        customer_name = customer_name or self.booking.customer_name or ""
        customer_phone = customer_phone or self.booking.customer_phone or ""
        customer_email = customer_email or self.booking.customer_email or ""
        
        contact, error = self._validate_booking_contact(customer_name, customer_phone, customer_email)
        
        if error:
            return error

        state_error = self._validate_booking_state( appointment_date, appointment_time, customer_confirmed )
        
        if state_error:
            return state_error

        customer_name, normalized_phone, normalized_email = contact
        
        print(f"[PHONE] Normalized: {normalized_phone}")

        try:
            print("[TOOL STATUS] Executing Booking...")
            result = await asyncio.to_thread(
                self.appointment_service.book_appointment,
                customer_name.strip(),
                normalized_phone,
                normalized_email,
                appointment_date,
                appointment_time
            )
                
            print(f"[TOOL] Book Appointment: {result}")
                
            if result.get("success") and result.get("booked"):
                self.booking.customer_name = customer_name.strip()
                self.booking.customer_phone = normalized_phone
                self.booking.customer_email = normalized_email

                self.booking.booking_completed = True
                self.booking.confirmation_pending = False
                self.booking.confirmed_by_customer = True

                self.booking.appointment_id = result.get("appointment_id")

                email_result = await asyncio.to_thread(
                    self.email_service.send_confirmation_email,
                    customer_email=normalized_email,
                    customer_name=customer_name.strip(),
                    appointment_id=result["appointment_id"],
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                )
                
                result.update(email_result)
                
                if result.get("email_sent"):
                    result["message"] = (
                        "Your Appointment is Confirmed and a Confirmation Email has been Sent!!"
                    )
                else:
                    result["message"] = (
                        "Your Appointment is Confirmed, but the Confirmation Email Could not be Sent."
                    )
                    
            return result
            
        except Exception as e:
            print("[TOOL ERROR] book_appointment")
            print(f"[TOOL ERROR TYPE] {type(e).__name__}")
            print(f"[TOOL ERROR MESSAGE] {e}")
            result = self._tool_error("book_appointment", e)
            result["booked"] = False
            return result

    @function_tool()
    async def find_alternative_slots(
        self,
        context: RunContext,
        appointment_date: str = "",
        appointment_time: str = "",
    ) -> dict:
        
        """Find nearby available 30-minute slots. Call this when a requested slot is unavailable or the customer asks for another/alternative time. If date or time is omitted, reuse the last slot checked in this conversation."""

        appointment_date = appointment_date or self.booking.appointment_date or ""
        appointment_time = appointment_time or self.booking.appointment_time or ""
        if not appointment_date or not appointment_time:
            return {
                "success": False,
                "slots": [],
                "error": "Ask the customer which date and time they want alternatives for.",
            }
        
        try:
            return await asyncio.to_thread(
                self.appointment_service.find_alternative_slots,
                appointment_date, appointment_time,
            )
        except Exception as error:
            return self._tool_error("find_alternative_slots", error)

    @function_tool()
    async def change_booking_slot(
        self, context: RunContext, appointment_date: str, appointment_time: str,
    ) -> dict:
        
        """Change the Pending Booking Date and Time after Checking Availability."""
        
        try:
            result = await asyncio.to_thread(
                self.appointment_service.check_availability,
                appointment_date, appointment_time,
            )
            
            if result.get("success") and result.get("available"):
                self.booking.appointment_date = appointment_date
                self.booking.appointment_time = appointment_time
                self.booking.availability_checked = True
                self.booking.slot_available = True
                self.booking.confirmed_by_customer = False
                self.booking.confirmation_pending = True
            return result
        
        except Exception as error:
            result = self._tool_error("change_booking_slot", error)
            result["available"] = False
            return result

    @function_tool()
    async def change_customer_details(
        self,
        context: RunContext,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
    ) -> dict:
        
        """Change the Pending Booking Customer's Name or Phone Number."""
        
        try:
            if customer_name.strip():
                self.booking.customer_name = customer_name.strip()
                
            if customer_phone.strip():
                normalized_phone = self.appointment_service.normalize_phone(customer_phone)
                
                if not self.appointment_service.is_valid_phone(normalized_phone):
                    raise ValueError("Invalid Phone Number!!.")
                self.booking.customer_phone = normalized_phone
            
            if customer_email.strip():
                normalized_email = customer_email.strip().lower()
                
                if not self.appointment_service.is_valid_email(normalized_email):
                    raise ValueError("Invalid Customer Email!!.")
                self.booking.customer_email = normalized_email
            
            self.booking.confirmed_by_customer = False
            self.booking.confirmation_pending = True
            
            return {
                "success": True,
                "customer_name": self.booking.customer_name,
                "customer_phone": self.booking.customer_phone,
                "customer_email": self.booking.customer_email,
                "message": "Customer details updated. Confirmation is required again.",
            }
            
        except Exception as error:
            return self._tool_error("change_customer_details", error)

    @function_tool()
    async def change_mind(self, context: RunContext) -> dict:
        
        """Cancel the Current Unbooked Booking Request without Changing Saved Appointments."""
        
        self.booking.reset()
        return {
            "success": True,
            "message": "The Pending Booking Request was Cancelled!!",
        }

    @function_tool()
    async def get_my_appointments(
        self,
        context: RunContext,
        customer_name: str = "",
        customer_phone: str = "",
        customer_email: str = "",
    ) -> dict:
        """List active appointments matching supplied customer identity details."""
        try:
            return await asyncio.to_thread(
                self.appointment_service.get_my_appointments,
                customer_name,
                customer_phone,
                customer_email,
            )
        except Exception as error:
            return self._tool_error("get_my_appointments", error)

    @function_tool()
    async def cancel_appointment(
        self,
        context: RunContext,
        appointment_id: str,
        customer_phone: str = "",
        customer_email: str = "",
        customer_name: str = "",
        customer_confirmed: bool = False,
    ) -> dict:
        """Cancel an owned appointment after explicit confirmation and identity verification."""
        if not customer_confirmed:
            return {
                "success": False,
                "cancelled": False,
                "error": "Customer Confirmation is Required Before Cancellation!!",
            }
        try:
            return await asyncio.to_thread(
                self.appointment_service.cancel_appointment,
                appointment_id,
                customer_phone,
                customer_email,
                customer_name,
            )
        except Exception as error:
            result = self._tool_error("cancel_appointment", error)
            result["cancelled"] = False
            return result

    @function_tool()
    async def reschedule_appointment(
        self,
        context: RunContext,
        appointment_id: str,
        new_date: str,
        new_time: str,
        customer_phone: str = "",
        customer_email: str = "",
        customer_name: str = "",
        customer_confirmed: bool = False,
    ) -> dict:
        """Move an owned appointment to a new available slot after confirmation."""
        if not customer_confirmed:
            return {
                "success": False,
                "rescheduled": False,
                "error": "Customer confirmation is required before rescheduling.",
            }
        try:
            return await asyncio.to_thread(
                self.appointment_service.reschedule_appointment,
                appointment_id,
                new_date,
                new_time,
                customer_phone,
                customer_email,
                customer_name,
            )
        except Exception as error:
            result = self._tool_error("reschedule_appointment", error)
            result["rescheduled"] = False
            return result