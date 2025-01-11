import stripe
from config import get_settings
from logger import logger

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripePaymentProvider:
    @staticmethod
    async def create_payment_intent(amount: float, currency: str, order_id: str):
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe использует центы
                currency=currency,
                metadata={'order_id': order_id},
                automatic_payment_methods={'enabled': True}
            )
            return intent.client_secret
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            raise PaymentError(str(e), "STRIPE_ERROR")

    @staticmethod
    async def confirm_payment(payment_intent_id: str):
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent.status == 'succeeded'
        except stripe.error.StripeError as e:
            logger.error(f"Stripe confirmation error: {str(e)}")
            raise PaymentError(str(e), "STRIPE_ERROR") 