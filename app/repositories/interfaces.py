"""Contratos da camada de repositórios.

Define as interfaces estruturais (Protocol) que os repositórios
concretos devem satisfazer. Os serviços dependem apenas destes
contratos, nunca das implementações SQLAlchemy — trocar o mecanismo de
persistência ou usar fakes nos testes não exige mudança nos serviços.
"""

from typing import Protocol

from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User


class UserRepository(Protocol):
    """Operações de persistência para usuários."""

    def get_by_id(self, user_id: int) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def create(self, user: User) -> User: ...

    def update(self, user: User) -> User: ...

    def list(self, offset: int, limit: int) -> list[User]: ...


class ProductRepository(Protocol):
    """Operações de persistência para produtos."""

    def get_by_id(self, product_id: int) -> Product | None: ...

    def list(
        self, offset: int, limit: int, only_active: bool
    ) -> tuple[list[Product], int]: ...

    def create(self, product: Product) -> Product: ...

    def update(self, product: Product) -> Product: ...


class OrderRepository(Protocol):
    """Operações de persistência para pedidos."""

    def get_by_id(self, order_id: int) -> Order | None: ...

    def add(self, order: Order) -> Order: ...

    def update(self, order: Order) -> Order: ...

    def list_by_user(self, user_id: int, offset: int, limit: int) -> list[Order]: ...


class PaymentRepository(Protocol):
    """Operações de persistência para pagamentos."""

    def create(self, payment: Payment) -> Payment: ...

    def update(self, payment: Payment) -> Payment: ...

    def get_pending_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None: ...

    def get_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None: ...

    def get_by_provider_payment_link_id(self, link_id: str) -> Payment | None: ...


__all__ = [
    "OrderRepository",
    "PaymentRepository",
    "ProductRepository",
    "UserRepository",
]
