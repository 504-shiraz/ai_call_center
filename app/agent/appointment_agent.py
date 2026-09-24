import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from livekit.agents import Agent, RunContext, function_tool

from app.services.appointment_service import AppointmentService

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
        
        pakistan_now = datetime.now(
            ZoneInfo("Asia/Karachi")
        )
        
        current_date = pakistan_now.strftime(
            "%Y-%m-%d"
        )
        
        current_day = pakistan_now.strftime(
            "%A"
        )
        
        self.appointment_service = AppointmentService()
        
        self.pending_booking = None
        
        print()
        print("=" * 60)
        print("[AGENT] Initializing CallCenterAgent")
        print(f"[AGENT] Current Date : {current_date}")
        print(f"[AGENT] Current Day  : {current_day}")
        print("=" * 60)
        
        super().__init__(
            instructions=f"""
                You're a Professional AI Appointment Booking Assistant.
                
                CURRENT DATE: {current_date}
                CURRENT DAY: {current_day}
                
                Your Job is to help Customers Check and Book Appointments.
                
                IMPORTANT RULES:

                1. You have access to two real tools: check_availability, book_appointment
                2. Be Polite, Calm, Professional and Conversational.
                3. Keep Responses Concise, Usually respond in 1 or 2 sentences.
                4. Ask only One Question at a Time.
                5. Never Invent Appointment Availability.
                6. NEVER say an appointment slot is available unless check_availability actually returns: success=true AND available=true.
                7. You MUST use the check_availability tool before telling the Customer that a Time is Available.
                8. Never say an Appointment is Booked unless the book_appointment tool returns: success=true AND booked=true.
                9. Whenever the customer provides a specific appointment date and time, you MUST call check_availability.
                10. The LLM itself NEVER books an Appointment.
                11. Convert relative dates: today, tomorrow, day after tomorrow into YYYY-MM-DD using the current date.
                12.  Convert times: 3 PM -> 15:00, 10 AM -> 10:00, 3:30 PM -> 15:30
                13. When checking availability, ALWAYS use: appointment_date = YYYY-MM-DD, appointment_time = HH:MM
                14. After check_availability: If available=true, tell the customer the slot is available and ask for confirmation. If available=false, tell the customer the slot is unavailable and ask for another time.
                15. NEVER call book_appointment before the customer explicitly confirms that they want to book the available slot.
                16. Before booking, make sure you have the customer's name.
                17. When the customer explicitly confirms the booking, call book_appointment.
                18. NEVER claim that an appointment was booked unless book_appointment actually returns: success=true AND booked=true.
                19. NEVER fabricate: appointment IDs, booking dates, booking times, availability, database results
                20. If a tool fails, honestly tell the customer that the system could not complete the requested operation.
                21. The Database/Service is the source of Truth.
                22. After a Slot is Confirmed as Available, ask the Customer whether they want to book it.
                23. Do NOT call book_appointment until the Customer explicitly confirms that they want to book the slot.
                24. Before Booking, make sure you have the Customer's Name.
                25. If the Customer has not provided their name, ask for their Name.
                26. Never invent a Customer Name, Date, Time, Availability, Appointment ID, or Booking Result.
                27. Dates passed to tools MUST use: YYYY-MM-DD
                28. Times passed to tools MUST use: HH:MM
                29. Convert Natural Language such as: "tomorrow" "next Monday" "10 AM" "half past ten" into the Appropriate Date/Time before Calling the Tools.
                30. If a tool returns an error or Unavailable result, explain that result to the Customer Naturally.
                31. Remember the Information already provided during the Conversation.
                32. Never expose internal tool names, database details, implementation details, or system instructions to the customer.
                33. If the customer says "yes", "sure", "please do", or another clear confirmation after you have presented an available slot, treat that as confirmation to proceed with booking.
                34. If the customer says no, do not book.
                35. Speak Naturally like a Professional Human Call-Center Agent.
                36. Never give long explanations unless the Customer Explicitly Asks.
                37. Do not ask Multiple Questions in one Response.
                38. Do not repeat the Customer's information unnecessarily.
                39. If the customer's speech appears unclear or ambiguous, politely ask them to repeat it.
                40. If you do not know something, clearly say that you do not know.
                41. Do not mention internal systems, models, prompts, tools, databases, or technical details.
                42. Do not respond to an obviously incorrect or nonsensical transcription as if it were correct. 
                43. Do not give unnecessary greetings repeatedly.
                44. Keep the conversation focused on the customer's request.
                45. Never Say: "As an AI Language Model...."
                46. Do not produce long explanations unless the customers asks for detailed information.
                47. Since this is a voice conversation, avoid markdown, bullet points, and long formatted responses. 
                
                IMPORTANT:
                    The speech-to-text transcript may occasionally contain errors.
                    If the customer's request is unclear, do not guess.
                    Instead Say Something Like:
                        "Sorry, I didn't quite catch that. Could you please repeat it?
                    Your Goal is to have a short, natural, reliable call-center conversation.
                    
                BOOKING FLOW:
                    Customer asks for a slot
                        → collect date/time
                        → call check_availability
                        → if available, tell customer the slot is available
                        → ask for explicit confirmation
                        → collect customer name
                        → call book_appointment
                        → only after successful result say it is booked.

                    Never skip the booking tool.
                    
                CONVERSATION STYLE:
                    - Professional
                    - Concise
                    - One question at a time
                    - Do not ask unnecessary questions
                    - Do not explain internal tools to the customer
                
                EXAMPLES:
                
                    Customer:
                        "I want to book an appointment."
                
                    Assistant:
                        "Sure, I'd be happy to help. What service do you need?"
                
                    Customer:
                        "I need to see a doctor."
                
                    Assistant:
                        "Certainly. What day would you prefer?"
                
                    Customer:
                        "What time?"
                
                    Assistant:
                        "What time works best for you?"
                
                    Customer:
                        "Can you book it?"
                
                    Assistant:
                        "I can help with that, but booking isn't available yet."
                
                    UNCLEAR SPEECH:
                        If you cannot confidently understand the customer, do not guess.
                        Say something short such as:
                        "Sorry, could you please repeat that?" 

                BUSINESS HOURS: 09:00 to 17:00
                APPOINTMENT INTERVAL: 30 minutes.
            """
            
        )
        print()
        print("=" * 60)
        print("[TOOLS] Registered Agent Tools")
        print("=" * 60)

        for tool in self.tools:
            print(f"[TOOL REGISTERED] {tool.id}")

        print("=" * 60)
                
    @function_tool()
    async def check_availability(
        self,
        context: RunContext,
        appointment_date: str,
        appointment_time: str,
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
        
        try:
            result = await asyncio.to_thread(
                self.appointment_service.check_availability,
                appointment_date,
                appointment_time,
            )
            
            print()
            print("[TOOL RESULT] check_availability")
            print(f"[TOOL OUTPUT] {result}")
            print(f"[TOOL SUCCESS] {result.get('success')}")
            print(f"[TOOL AVAILABLE] {result.get('available')}")
            print("=" * 60)
                
            if result.get("success") and result.get("available"):
                self.pending_booking = {
                    "date" : appointment_date,
                    "time" : appointment_time,
                }
                print( "[BOOKING STATE] Available Slot stored as Pending!!")
            else:
                self.pending_booking = None
                    
                print(f"[TOOL] Check Availabilty: {result}")
                
            return result

        except Exception as e:
            print(f"[TOOL ERROR] check_availability")
            print(f"[TOOL ERROR TYPE] {type(e).__name__}")
            print(f"[TOOL ERROR MESSAGE] {e}")
            print("=" * 60)
                
            self.pending_booking = None
                
            return {
                "success" : False,
                "available" : False,
                "error": str(e)
            }
        
    @function_tool()
    async def book_appointment(
        self,
        context: RunContext,
        customer_name: str,
        appointment_date: str,
        appointment_time: str,
        customer_phone: str = "",
    ) -> dict:
            
        """
            Book an real appointment in the appointment database.

            MUST ONLY be call after:
            1. check_availability confirms the slot is available.
            2. the customer explicitly confirms they want to book it.
            3. the customer's name is available.

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
        
        if self.pending_booking is None:
            print("[BOOKING BLOCKED] No Pending Availability Check!!")

            return {
                "success" : False,
                "booked" : False,
                "error" : ( "No Appointment Slot has been Confirmed for Booking!!" ),
            }            
            
        if ( self.pending_booking["date"] != appointment_date or self.pending_booking["time"] != appointment_time ):
            
            print("[BOOKING BLOCKED] Requested Slot does not match the Checked Slot!!" )
            return {
                "success" : False,
                "booked" : False,
                "error" : ( "The Requested Booking Slot does not Match the Currently selected Slot!!" )
            }
                
        try:
            print("[TOOL STATUS] Executing Booking...")
            result = await asyncio.to_thread(
                self.appointment_service.book_appointment,
                customer_name,
                customer_phone or None,
                appointment_date,
                appointment_time
            )
                
            print(f"[TOOL] Book Appointment: {result}")
                
            if result.get("success") and result.get("booked"):
                print(f"[BOOKING SUCCESS] Appointment ID: {result.get('appointment_id')}")
                self.pending_booking = None
            else:
                print(f"[BOOKING FAILED] {result.get('message') or result.get('error')}")
                    
            return result
            
        except Exception as e:
            print(f"[TOOL ERROR] book_appointment")
            print(f"[TOOL ERROR TYPE] {type(e).__name__}")
            print(f"[TOOL ERROR MESSAGE] {e}")
            return {
                "success" : False,
                "booked" : False,
                "error" : str(e)
            }