"""Integração com o Stripe (Checkout Session / Payment Link).

Stripe espera valores em unidades menores (centavos no Brasil) e moeda
"BRL" minúscula. Todos os eventos de retorno são verificados pela
assinatura do webhook, nunca pela confiança no corpo do request.
"""

import logging
from typing import Any

import stripe
from fastapi import HTTPException, status

from app.payment_providers import (
    PaymentGatewayError,
    ProviderLinkResult,
    ProviderPaymentDetails,
)


logger = logging.getLogger(__name__)


class StripePaymentLink:
    """Provedor Stripe, isolando a API do gateway do resto da aplicação."""

    def __init__(self, api_key: str, webhook_secret: str | None) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        # Stripe usa uma variável global de módulo; setada por instância.
        stripe.api_key = api_key

    def create_payment_link(
        self,
        order_id: int,
        amount_cents: int,
        user_email: str,
        user_name: str,
    ) -> ProviderLinkResult:
        """Cria uma Checkout Session de R$amount_cents para o pedido."""
        from app.config import get_settings

        base_url = get_settings().base_url.rstrip("/")
        try:
            # Valores em centavos (unidade menor do Stripe) e moeda BRL.
            session = stripe.checkout.Session.create(
                mode="payment",
                customer_email=user_email,
                line_items=[
                    {
                        "price_data": {
                            "currency": "brl",
                            "product_data": {
                                "name": f"Order #{order_id}",
                                "description": f"payment for order #{order_id} by {user_name}",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=f"{base_url}/api/v1/payments/success",
                cancel_url=f"{base_url}/api/v1/payments/failed",
                metadata={"order_id": str(order_id)},
            )
        except stripe.error.StripeError as exc:
            # Log local sem expor stack trace na resposta HTTP.
            logger.exception("stripe checkout session creation failed")
            raise PaymentGatewayError("unable to create stripe payment link") from exc

        return ProviderLinkResult(
            payment_link=session.url or "",
            provider_payment_link_id=session.id,
        )

    def get_payment_details(self, payment_id: str) -> ProviderPaymentDetails:
        """Consulta uma Checkout Session e devuelve estado normalizado."""
        try:
            session = stripe.checkout.Session.retrieve(payment_id)
        except stripe.error.StripeError:
            logger.exception("failed to fetch stripe payment details")
            raise PaymentGatewayError("unable to fetch payment details") from None

        is_paid = session.payment_status == "paid"
        return ProviderPaymentDetails(
            payment_id=session.id,
            amount_cents=int(session.amount_total or 0),
            currency=str(session.currency or "").upper(),
            status=str(session.payment_status),
            is_paid=is_paid,
            raw_payment_id=getattr(session, "payment_intent", None),
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict[str, Any]:
        """Verifica a assinatura do webhook e retorna o evento como dict.

        Lança PaymentGatewayError se o segredo não está configurado ou a
        assinatura não confere (possível fraude/replay).
        """
        if not self._webhook_secret:
            raise PaymentGatewayError("stripe webhook secret not configured")
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self._webhook_secret
            )
        except Exception as exc:
            logger.warning("stripe webhook signature verification failed")
            raise PaymentGatewayError("invalid webhook signature") from exc
        return event
