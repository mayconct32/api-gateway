from pydantic import Basemodel
from enum import Enum


# essas classes de schemas do pydantic estao estao no lugar errado, e algumas estao inacabadas. Por favor, faça esse ajuste


class PaymentProvider(str, Enum):
    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"


class CreatePaymentLinkRequest(Basemodel):
    order_id: int
    provider: PaymentProvider


class PaymentLinkResponse(BaseModel):
    order_id: int
    provider: PaymentProvider
    amount: float
    currency: str
    payment_link: str
    provider_payment_link_id: str #deve ser int(engano do meu professor)


from abc import ABC, abstractmethod


#faça uma interface um pouco melhorzinha, essa aqui está inacabada(PaymentProvider)
# esse nao é o lugar dele, mas estou com sono
class PaymentProvider(ABC):
    pass