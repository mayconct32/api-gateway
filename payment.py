from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey, String, Float


class Payment(DeclarativeBase):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR") #mude para a moeda local brasileira(REAL)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")

    payment_link_uri: Mapped[str] = mapped_column(String(500), nullable=False)

    provider_payment_link_id: Mapped[str] = mapped_column(String(255), nullable=False)

    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)