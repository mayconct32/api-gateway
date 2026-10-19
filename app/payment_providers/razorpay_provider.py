"""Integração com o Razorpay (Payment Link).

Histórico do projeto: o código original usava rúpias/INR e paisa.
Ajustado para o contexto brasileiro: valores em centavos e moeda BRL
(1 real = 100 centavos, mesma regra de unidades menores usada pelo
Razorpay para paisa). O SDK é importado como cliente declarado: o
método client.payment_link.create cria o link e client.payment_link.fetch
verifica o estado do pagamento sem depender do callback.
"""

import logging

import razorpay

from app.payment_providers import (
    PaymentGatewayError,
    ProviderLinkResult,
    ProviderPaymentDetails,
)


logger = logging.getLogger(__name__)


class RazorpayPaymentLink:
    """Provedor Razorpay, escondendo detalhes do SDK do resto da app."""

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str | None) -> None:
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret
        # razo.py exports Client em módulo de mesmo nome: a instância
        # autenticada é criada uma vez por request (barato, HTTP/keepalive).
        self._client = razorpay.Client(auth=(key_id, key_secret))

    def create_payment_link(
        self,
        order_id: int,
        amount_cents: int,
        user_email: str,
        user_name: str,
    ) -> ProviderLinkResult:
        """Cria um Payment Link Razorpay para o valor em centavos BRL."""
        from app.config import get_settings

        base_url = get_settings().base_url.rstrip("/")
        create_request = {
            # Centavos em BRL: o Razorpay exige unidades menores (paisa/centavos)
            "amount": amount_cents,
            "currency": "BRL",
            "accept_partial": False,
            "reference_id": f"order_{order_id}",
            "description": f"payment for order #{order_id}",
            "customer": {
                "name": user_name,
                "email": user_email,
            },
            # Notificações por e-mail/sms desligadas: a url do link é devolvida
            # diretamente ao usuário da API.
            "notify": {"sms": False, "email": False},
            "callback_url": f"{base_url}/api/v1/payments/success",
            "callback_method": "get",
        }
        try:
            response = self._client.payment_link.create(create_request)
        except Exception as exc:
            logger.exception("razorpay payment link creation failed")
            raise PaymentGatewayError("unable to create razorpay payment link") from exc

        return ProviderLinkResult(
            payment_link=response["short_url"],
            provider_payment_link_id=response["id"],
        )

    def get_payment_details(self, payment_id: str) -> ProviderPaymentDetails:
        """Busca o pagamento Razorpay e normaliza o estado."""
        try:
            payment = self._client.payment_link.fetch(payment_id)
        except Exception:
            logger.exception("failed to fetch razorpay payment details")
            raise PaymentGatewayError("unable to verify razorpay payment") from None

        # status razo.py: created/paid/cancelled/expired
        is_paid = payment.get("status") == "paid"
        cents = int(payment.get("amount") or 0)
        return ProviderPaymentDetails(
            payment_id=payment["id"],
            amount_cents=cents,
            currency=str(payment.get("currency") or "").upper(),
            status=str(payment.get("status")),
            is_paid=is_paid,
            raw_payment_id=payment.get("id"),
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict:
        """Valida X-Razorpay-Signature (HMAC SHA256 do payload cru).

        Lança PaymentGatewayError se o segredo não está configurado ou
        a assinatura não confere.
        """
        import hmac
        import hashlib

        if not self._webhook_secret:
            raise PaymentGatewayError("razorpay webhook secret not configured")
        expected = hmac.new(
            self._webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        # compare_digest evita timing attack na comparação da assinatura.
        if not hmac.compare_digest(expected, signature or ""):
            logger.warning("razorpay webhook signature verification failed")
            raise PaymentGatewayError("invalid webhook signature")

        # O payload do Razorpay é JSON; parsed aqui para que o webhook
        # do serviço trabalhe apenas com o dicionário de dados.
        import json

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PaymentGatewayError("invalid webhook payload") from exc
