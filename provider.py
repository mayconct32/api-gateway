"""pip install razorpay | poetry add razorpay"""

from fastapi import HTTPException, status
import razorpay # type: ignore
import stripe # type: ignore
import os 

from schemas import PaymentProvider


class RazorpayProvider(PaymentProvider):
    """classe pra serviços do provedor gateway"""
    def __init__(self) -> None:
        self.client = razorpay.client(
            auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
        )

    def create_payment_link(
        self, order_id: int, amount: float, user_email: str, user_name: str
    ) -> dict:

        # 1 ruppes = 100 paisa   (converta em real)
        create_payment_link_request = {
            "amount": amount*100,
            "currency": "INR", #converta para real
            "accept_partial": False,
            "reference_id": f"order_{order_id}",
            "description": f"payment for order #{order_id}",
            "customer": {
                "name": user_name,
                "email": user_email
            },
            "notify": {
                "sms": False,
                "email": False #testar com True depois
            },
            "callback_url": "http://localhost:8000/api/v1/payments/razorpay/success",
            "callback_method": "get"
        }   

        try:
            response = self.client.payment_link_create(create_payment_link_request)
        except Exception as exc:
            raise HTTPException(
                status_code=status.WS_1014_BAD_GATEWAY,
                detail="unable to create razorpay payment link"
            )

        print(f"response: {response}")

        return {
            "payment_link": response["short_url"],
            "provider_payment_link_id": response["id"]
        }

    def get_payment_details(self, payment_id: str) -> dict:
        try:
            payment=self.client.payment.fetch(payment_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.WS_1014_BAD_GATEWAY,
                detail='unable to verify razorpay payment'
            )

        print(
            "payment details: ", 
            payment["id"], 
            payment["amount"], 
            payment["status"]
        )

        return {
            "payment_id": payment["id"],
            "amount": payment["amount"],
            "status": payment["status"],
            "is_paid": payment["status"] == "captured"
        }


"""pip install stripe | poetry add stripe"""

# criar interface de provedor, para que nao deixar o código acoplado
class StripeProvider(PaymentProvider):
    def __init__(self):
        # utilizar classe Settings(baseSettings) do pydantic_settings mais pra frente
        stripe.api_key = os.getenv("STRIPE_API_KEY")

    def create_payment_link(
        self,
        order_id: int,
        amount: float,
        user_email: str,
        user_name: str
    ) -> dict:
        try:

            session=stripe.checkout.Session.create(
                mode="payment",
                customer_email=user_email,
                line_items=[
                    {
                        "price_data":{
                            "currency": "inr", #trocar por real
                            "product_data": {
                                "name": f"Order #{order_id}",
                                "description": f"payment for order #{order_id} by {user_name}"
                            },
                            "unit_amount": round(amount*100)
                        },
                        "quantity": 1
                    }
                ],
                success_url="http://localhost:8000/api/v1/payments/success",
                cancel_url="http://localhost:8000/api/v1/payments/failed",
                metadata = {
                    "order_id": str(order_id)
                }
            )

            print(f"session: {session}")

            return {
                "payment_link": session.url,
                "provider_payment_link_id": session.id
            }

        
        except Exception as exc:
            raise HTTPException(

                status_code = status.HTTP_502_BAD_GATEWAY,
                detail = "unable to create stripe payment link"
            )

    def get_payment_details(self, payment_id: str) -> dict:
        try:
            session=stripe.checkout.Session.retrieve(payment_id)

            #log improvisado
            print(session)

            return {
                "payment_id": session.id,
                "amount": session.amount_total,
                "status": session.payment_status,
                "is_paid": session.payment_status == "paid"
            }
        except Exception as exc:
            raise HTTPException(
                status_code = status.HTTP_502_BAD_GATEWAY,
                detail = "unable to fetch payment details"
            )