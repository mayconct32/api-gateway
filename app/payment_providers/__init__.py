"""Fabrica e define o contrato dos provedores de pagamento.

Stripe e Razorpay têm APIs muito diferentes, mas expostas através de
uma interface estrutural (Protocol) única: o serviço de pagamento
consome apenas esta interface, sem conhecer detalhes de cada gateway.
"""

from typing import Any, Protocol, TypedDict

from app.config import Settings
from app.enums import PaymentProviderEnum


class PaymentGatewayError(Exception):
    """Erro ao comunicar com o gateway externo.

    Detalhes internos (stack traces, corpo da resposta do provedor)
    não são expostos: o serviço traduz para HTTP 502 com mensagem
    genérica e registra o log completo fora da resposta HTTP.
    """


class ProviderLinkResult(TypedDict):
    payment_link: str
    provider_payment_link_id: str


class ProviderPaymentDetails(TypedDict):
    payment_id: str
    amount_cents: int
    currency: str
    status: str
    is_paid: bool
    # Some gateways return the id of the underlying charge/payment
    # separate from the link/session id; useful for reconciliation.
    raw_payment_id: str | None


class PaymentLinkProvider(Protocol):
    """Provedor capaz de criar links de pagamento e verificar pagamentos.

    Implementado por StripePaymentLink e RazorpayPaymentLink; os testes
    usam fakes que também satisfazem este protocolo.
    """

    def create_payment_link(
        self,
        order_id: int,
        amount_cents: int,
        user_email: str,
        user_name: str,
    ) -> ProviderLinkResult: ...

    def get_payment_details(self, payment_id: str) -> ProviderPaymentDetails: ...


def build_payment_providers(
    settings: Settings,
) -> dict[PaymentProviderEnum, PaymentLinkProvider]:
    """Instancia os provedores cujas credenciais estão configuradas."""
    from app.payment_providers.razorpay_provider import RazorpayPaymentLink
    from app.payment_providers.stripe_provider import StripePaymentLink

    providers: dict[PaymentProviderEnum, PaymentLinkProvider] = {}

    if settings.stripe_api_key:
        providers[PaymentProviderEnum.STRIPE] = StripePaymentLink(
            api_key=settings.stripe_api_key,
            webhook_secret=settings.stripe_webhook_secret,
        )
    if settings.razorpay_key_id and settings.razorpay_key_secret:
        providers[PaymentProviderEnum.RAZORPAY] = RazorpayPaymentLink(
            key_id=settings.razorpay_key_id,
            key_secret=settings.razorpay_key_secret,
            webhook_secret=settings.razorpay_webhook_secret,
        )
    return providers


def get_webhook_secret_for(provider: PaymentProviderEnum, settings: Settings) -> str:
    """Retorna o segredo de webhook configurado para o provedor."""
    if provider is PaymentProviderEnum.STRIPE:
        return settings.stripe_webhook_secret or ""
    if provider is PaymentProviderEnum.RAZORPAY:
        return settings.razorpay_webhook_secret or ""
    return ""
