from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import OrderStatus
from app.models.base import Base


class Order(Base):
    """Pedido de um usuário, com total recalculado sempre no servidor."""

    __tablename__ = "orders"
    __table_args__ = (
        # Integridade financeira: o total nunca pode ficar negativo.
        CheckConstraint("total_cents >= 0", name="ck_orders_total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=OrderStatus.PENDING.value)
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")  # noqa: F821


class OrderItem(Base):
    """Item de um pedido, com snapshot do preço unitário em centavos."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Preço unitário congelado no momento da compra, em centavos. Em caso
    # de alteração posterior do preço do produto, o histórico do pedido
    # não é afetado.
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
