import stripe
import config

stripe.api_key = config.STRIPE_SECRET_KEY

class PaymentHandler:
    PLANS = {
        "starter": {
            "name": "Starter",
            "price_id": "price_starter_monthly",
            "amount": 2500,
            "currency": "usd"
        },
        "growth": {
            "name": "Growth",
            "price_id": "price_growth_monthly",
            "amount": 6000,
            "currency": "usd"
        },
        "enterprise": {
            "name": "Enterprise",
            "price_id": "price_enterprise_monthly",
            "amount": 15000,
            "currency": "usd"
        }
    }
    
    def create_checkout_session(self, plan_type: str, client_email: str):
        plan = self.PLANS.get(plan_type)
        if not plan:
            raise ValueError(f"Invalid plan: {plan_type}")
        
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': plan['currency'],
                        'product_data': {
                            'name': f"LeaseAI - {plan['name']}",
                        },
                        'unit_amount': plan['amount'],
                        'recurring': {'interval': 'month'}
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                customer_email=client_email,
                success_url='http://localhost:8501?payment=success',
                cancel_url='http://localhost:8501?payment=cancelled',
            )
            return session.url
        except Exception as e:
            raise Exception(f"Checkout error: {str(e)}")