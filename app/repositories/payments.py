from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import PaymentStatus
from app.models.payment import Payment
from app.repositories.interfaces import PaymentRepository as PaymentRepositoryProtocol


class PaymentRepository(PaymentRepositoryProtocol):
    """Implementação SQLAlchemy de persistência de pagamentos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payment: Payment) -> Payment:
        """Persiste um novo payment e devolve a instância recarregada."""
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update(self, payment: Payment) -> Payment:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_pending_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None:
        """Payment link ainda pendente deste pedido/provedor, se existir.

        Usado para idempotência: quando o usuário pedir para pagar o
        mesmo pedido com o mesmo provedor, o link anterior é reutilizado
        em vez de criar outro cobrança no gateway.
        """
        statement = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.provider == provider,
                Payment.status == PaymentStatus.PENDING.value,
            )
            .order_by(Payment.id.desc())
        )
        return self.db.scalars(statement).first()

    def get_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None:
        """Último payment registrado para o pedido/provedor."""
        statement = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.provider == provider,
            )
            .order_by(Payment.id.desc())
        )
        return self.db.scalars(statement).first()

    def get_by_provider_payment_link_id(self, link_id: str) -> Payment | None:
        """Localiza o Payment pelo id do link no gateway (webhooks)."""
        statement = select(Payment).where(
            Payment.provider_payment_link_id == link_id
        )
        return self.db.scalars(statement).first()
