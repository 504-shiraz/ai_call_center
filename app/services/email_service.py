import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

class ConfirmationEmailService:
    def send_confirmation_email(
        self,
        customer_email: str,
        customer_name: str,
        appointment_id: str,
        appointment_date: str,
        appointment_time: str,
    ) -> dict:
        if not settings.EMAIL_ENABLED:
            logger.warning("confirmation email disabled appointment_id=%s", appointment_id)
            return {
                "email_sent": False,
                "email_error": "Confirmation Email delivery is Disabled.",
            }

        required_settings = {
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        }
        missing_settings = [name for name, value in required_settings.items() if not value]
        if missing_settings:
            error = "Missing email configuration: " + ", ".join(missing_settings)
            logger.error("confirmation email not configured appointment_id=%s missing=%s", appointment_id, missing_settings)
            return {
                "email_sent": False,
                "email_error": error,
            }

        message = EmailMessage()
        message["Subject"] = f"Appointment Confirmation - {appointment_id}"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = customer_email
        message.set_content(
            f"Hello {customer_name},\n\n"
            "Your Appointment has been Confirmed.\n\n"
            f"Appointment ID: {appointment_id}\n"
            f"Date: {appointment_date}\n"
            f"Time: {appointment_time}\n\n"
            "Thank you."
        )

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            logger.exception("confirmation email failed appointment_id=%s", appointment_id)
            return {
                "email_sent": False,
                "email_error": str(error),
            }

        logger.info("confirmation email sent appointment_id=%s", appointment_id)
        return {
            "email_sent": True,
            "email_error": None,
        }
