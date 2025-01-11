from twilio.rest import Client
from config import get_settings
from logger import logger

settings = get_settings()
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

class SMSService:
    @staticmethod
    async def send_sms(phone_number: str, message: str):
        try:
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"SMS sent successfully: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            raise 