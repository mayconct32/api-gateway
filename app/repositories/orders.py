from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.repositories.interfaces import OrderRepository as OrderRepositoryProtocol


class OrderRepository(OrderRepositoryProtocol):
    """Implementação SQLAlchemy de persistência de pedidos."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, order_id: int) -> Order | None:
        # selectin já carrega itens e evita N+1 ao serializar o pedido.
        statement = select(Order).where(Order.id == order_id)
        return self.db.scalars(statement).first()

    def add(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        self.db.commit()
        self.db.refresh(order)
        return order

    def list_by_user(self, user_id: int, offset: int = 0, limit: int = 50) -> list[Order]:
        statement = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement))
