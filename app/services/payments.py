"""Regras de negócio de pagamentos (links, verificação e webhooks).

Integridade financeira: valores usados na cobrança vêm do pedido no
banco, nunca do cliente. A confirmação usa apenas dados verificados no
gateway (consulta direta ou webhook com assinatura validada).
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.enums import OrderStatus, PaymentProviderEnum, PaymentStatus
from app.exceptions import (
    AccessDeniedError,
    InvalidOperationError,
    NotFoundError,
    PaymentProviderUnavailableError,
)
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User, UserRole
from app.payment_providers import (
    PaymentGatewayError,
    PaymentLinkProvider,
)
from app.repositories import interfaces
from app.repositories.orders import OrderRepository
from app.repositories.payments import PaymentRepository
from app.schemas.payments import (
    CreatePaymentLinkRequest,
    PaymentLinkResponse,
    PaymentVerifyResponse,
    VerifyPaymentRequest,
)


logger = logging.getLogger(__name__)


class PaymentService:
    """Serviço de pagamento, com provedores injetados (Stripe/Razorpay)."""

    def __init__(
        self,
        db: Session,
        providers: dict[PaymentProviderEnum, PaymentLinkProvider],
    ) -> None:
        self.db = db
        self.order_repository: interfaces.OrderRepository = OrderRepository(db)
        self.payment_repository: interfaces.PaymentRepository = PaymentRepository(db)
        self.providers = providers

    def _provider_for(self, provider: PaymentProviderEnum) -> PaymentLinkProvider:
        """Provedor solicitado, se estiver configurado na aplicação.

        Provedor válido porém sem credenciais configuradas é erro do
        ambiente, não do cliente (a tradução aponta como indisponibilidade).
        """
        provider_instance = self.providers.get(provider)
        if provider_instance is None:
            raise PaymentProviderUnavailableError("payment provider is not available")
        return provider_instance

    def _get_owned_order(self, order_id: int, current_user: User) -> Order:
        """Pedido pelo id, garantindo que só o dono (ou ADMIN) acesse."""
        order = self.order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError("order not found")
        if order.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise AccessDeniedError("access denied")
        return order

    def _validate_order_for_payment(self, order: Order) -> None:
        """Só pedidos pendentes e não pagos aceitam novo pagamento."""
        if order.status != OrderStatus.PENDING.value:
            raise InvalidOperationError("payment link can be created for pending order")
        if order.payment_status == PaymentStatus.PAID.value:
            raise InvalidOperationError("order is already paid")

    def create_payment(
        self, current_user: User, payload: CreatePaymentLinkRequest
    ) -> PaymentLinkResponse:
        """Cria (ou reutiliza) o link de pagamento de um pedido.

        Idempotência: um link pendente por (pedido, provedor) é
        reutilizado quando o usuário pedir o pagamento novamente,
        evitando cobranças duplicadas no gateway.
        """
        order = self._get_owned_order(payload.order_id, current_user)
        self._validate_order_for_payment(order)

        existing_payment = self.payment_repository.get_pending_by_order_and_provider(
            order.id, payload.provider.value
        )
        if existing_payment is not None:
            return PaymentLinkResponse(
                order_id=order.id,
                provider=payload.provider,
                amount=existing_payment.amount_cents / 100,
                currency=existing_payment.currency,
                payment_link=existing_payment.payment_link_uri,
                provider_payment_link_id=existing_payment.provider_payment_link_id,
            )

        provider = self._provider_for(payload.provider)
        try:
            provider_response = provider.create_payment_link(
                order_id=order.id,
                amount_cents=order.total_cents,
                user_name=current_user.full_name,
                user_email=current_user.email,
            )
        except PaymentGatewayError as exc:
            logger.exception("payment link creation failed for order %s", order.id)
            raise PaymentProviderUnavailableError(str(exc)) from exc

        payment = Payment(
            order_id=order.id,
            user_id=current_user.id,
            provider=payload.provider.value,
            # BRL: valor em centavos direto do pedido.
            amount_cents=order.total_cents,
            currency="BRL",
            status=PaymentStatus.PENDING.value,
            payment_link_uri=provider_response["payment_link"],
            provider_payment_link_id=provider_response["provider_payment_link_id"],
        )
        db_payment = self.payment_repository.create(payment)

        return PaymentLinkResponse(
            order_id=order.id,
            provider=payload.provider,
            amount=db_payment.amount_cents / 100,
            currency=db_payment.currency,
            payment_link=db_payment.payment_link_uri,
            provider_payment_link_id=db_payment.provider_payment_link_id,
        )

    def _mark_order_paid(self, payment: Payment) -> None:
        """Marca pagamento e pedido como pagos em uma única transação.

        Estado anterior ainda PENDING garante idempotência: eventos
        repetidos de webhook ou verificações duplicadas não reprocessam
        a mesma atualização.
        """
        order = self.order_repository.get_by_id(payment.order_id)
        if order is None:  # pragma: no cover - FK garante o pedido
            raise NotFoundError("order not found")

        if order.payment_status != PaymentStatus.PAID.value:
            # Um único commit cobre payment + order (integridade: os dois
            # estados mudam juntos ou nenhum muda).
            payment.status = PaymentStatus.PAID.value
            order.payment_status = PaymentStatus.PAID.value
            order.status = OrderStatus.CONFIRMED.value
            self.db.commit()

    def verify_payment(
        self, current_user: User, payload: VerifyPaymentRequest
    ) -> PaymentVerifyResponse:
        """Confirmação solicitada pelo cliente (URL de retorno).

        Os dados vêm do gateway (fetch direto) e são comparados com o
        pedido no banco: valor e moeda devem coincidir com o registrado
        no servidor. Nunca se confia em estados enviados pelo cliente.
        """
        order = self._get_owned_order(payload.order_id, current_user)
        provider = self._provider_for(payload.provider)
        payment = self.payment_repository.get_by_order_and_provider(
            order.id, payload.provider.value
        )
        if payment is None:
            raise NotFoundError("payment not found")

        # Idempotência: pedido já pago retorna o estado atual sem reprocessar.
        if payment.status == PaymentStatus.PAID.value:
            return PaymentVerifyResponse(
                order_id=order.id,
                payment_status=PaymentStatus.PAID.value,
                order_status=order.status,
                provider=payload.provider,
                payment_id=payment.provider_payment_id or payload.payment_id,
            )

        try:
            provider_payment = provider.get_payment_details(payload.payment_id)
        except PaymentGatewayError as exc:
            logger.exception("payment verification failed for order %s", order.id)
            raise PaymentProviderUnavailableError(str(exc)) from exc

        # Valor do pagamento (centavos) deve corresponder ao cobrado pelo
        # servidor; divergentes indicam manipulação ou cobrança errada.
        if int(provider_payment["amount_cents"]) != int(payment.amount_cents):
            logger.warning(
                "payment amount mismatch: expected %s got %s (order %s)",
                payment.amount_cents,
                provider_payment["amount_cents"],
                order.id,
            )
            raise InvalidOperationError("payment amount does not match order amount")
        if not provider_payment["is_paid"]:
            raise InvalidOperationError("payment not completed")

        payment.provider_payment_id = (
            provider_payment["raw_payment_id"] or provider_payment["payment_id"]
        )
        self._mark_order_paid(payment)

        return PaymentVerifyResponse(
            order_id=order.id,
            payment_status=PaymentStatus.PAID.value,
            order_status=order.status,
            provider=payload.provider,
            payment_id=payment.provider_payment_id or "",
        )

    def handle_webhook(
        self,
        provider: PaymentProviderEnum,
        event: dict[str, Any],
    ) -> dict[str, str]:
        """Processa evento de webhook já validado por assinatura.

        Prevenção contra processamento repetido do mesmo evento: o
        status do payment é a chave de idempotência — eventos repetidos
        (ou retrays do gateway) não alteram novamente o estado do pedido.
        """
        if provider is PaymentProviderEnum.STRIPE:
            obj = event.get("data", {}).get("object", {})
            link_id = str(obj.get("id") or "")
            event_type = str(event.get("type") or "")
            # Eventos de sucesso do Stripe Checkout.
            paid = (
                event_type == "checkout.session.completed"
                and obj.get("payment_status") == "paid"
            )
            amount_cents = obj.get("amount_total")
            currency = str(obj.get("currency") or "").upper()
            raw_payment_id = obj.get("payment_intent")
        else:  # RAZORPAY
            entities = (
                event.get("payload", {}).get("payment_link", {}).get("entity", {})
            )
            link_id = str(entities.get("id") or "")
            event_type = str(event.get("event") or "")
            paid = event_type == "payment_link.paid"
            amount_cents = entities.get("amount")
            currency = str(entities.get("currency") or "").upper()
            raw_payment_id = entities.get("id")

        if not link_id:
            # Evento sem referência ao link: nada a processar com segurança.
            return {"status": "ignored"}

        payment = self.payment_repository.get_by_provider_payment_link_id(link_id)
        if payment is None:
            raise NotFoundError("payment not found")

        if payment.status == PaymentStatus.PAID.value:
            return {"status": "already_processed"}

        if not paid:
            # Outros eventos (expirados, cancelados, criados) são apenas
            # reconhecidos, sem mudar o estado para pago.
            return {"status": "ignored"}

        # Defesa em profundidade: mesmo com assinatura válida o valor do
        # evento precisa bater com o valor registrado no servidor.
        if amount_cents is not None and int(amount_cents) != int(payment.amount_cents):
            logger.warning(
                "webhook amount mismatch: expected %s got %s (payment %s)",
                payment.amount_cents,
                amount_cents,
                link_id,
            )
            return {"status": "amount_mismatch"}
        if currency and currency != payment.currency:
            logger.warning(
                "webhook currency mismatch: expected %s got %s (payment %s)",
                payment.currency,
                currency,
                link_id,
            )
            return {"status": "currency_mismatch"}

        payment.provider_payment_id = str(raw_payment_id or link_id)
        self._mark_order_paid(payment)

        return {"status": "processed"}
