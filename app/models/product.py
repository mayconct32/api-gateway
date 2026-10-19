from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    """Produto do catálogo, com preço em centavos e exclusão lógica."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Preço em centavos. Inteiro evita erros de arredondamento de ponto
    # flutuante e divergência entre backend, gateways e banco.
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - apenas debug
        return f"Product(id={self.id!r}, name={self.name!r}, price_cents={self.price_cents!r})"
