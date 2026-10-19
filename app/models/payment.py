from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import PaymentStatus
from app.models.base import Base


class Payment(Base):
    """Registro de uma tentativa de pagamento associada a um Order.

    Moeda e valor em centavos, comprados pelo backend: o cliente nunca
    envia valores. Idempotência por provedor: um único payment link
    pendente por (order_id, provider) — evita links duplicados.
    """

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "provider", "provider_payment_link_id",
            name="uq_payments_order_provider_link",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL")

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PaymentStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    payment_link_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    provider_payment_link_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped["Order"] = relationship(back_populates="payments")  # noqa: F821
