from pydantic import BaseModel

from app.enums import PaymentProviderEnum


class CreatePaymentLinkRequest(BaseModel):
    """Escolha de provedor para gerar o link de pagamento de um pedido.

    Valores, status e moeda não são aceitos aqui: são calculados no
    servidor a partir do pedido e dos produtos no banco.
    """

    order_id: int
    provider: PaymentProviderEnum


class PaymentLinkResponse(BaseModel):
    """Dados do link gerado (ou pendente) para o pedido."""

    order_id: int
    provider: PaymentProviderEnum
    amount: float
    currency: str
    payment_link: str
    provider_payment_link_id: str


class VerifyPaymentRequest(BaseModel):
    """Solicitação de confirmação de pagamento na volta do gateway."""

    order_id: int
    provider: PaymentProviderEnum
    # id do pagamento retornado pelo provedor na URL de retorno;
    # é uma string tanto para Stripe (cs_...) quanto para Razorpay.
    payment_id: str


class PaymentVerifyResponse(BaseModel):
    """Estado combinado de pagamento e pedido após a verificação."""

    order_id: int
    payment_status: str
    order_status: str
    provider: PaymentProviderEnum
    payment_id: str
