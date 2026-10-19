"""Contratos da camada de repositórios.

Define as interfaces estruturais (Protocol) que os repositórios
concretos devem satisfazer. Os serviços dependem apenas destes
contratos, nunca das implementações SQLAlchemy — trocar o mecanismo de
persistência ou usar fakes nos testes não exige mudança nos serviços.
"""

from typing import Protocol

from app.models.order import Order
from app.models.payment import Payment
from app.models.product import Product
from app.models.user import User


class UserRepository(Protocol):
    """Operações de persistência para usuários."""

    def get_by_id(self, user_id: int) -> User | None:
        """Recupera o usuário pelo id, ou None se inexistente."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Recupera o usuário pelo e-mail, ou None se inexistente."""
        ...

    def create(self, user: User) -> User:
        """Persiste um novo usuário e devolve a instância recarregada."""
        ...

    def update(self, user: User) -> User:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        ...

    def list(self, offset: int, limit: int) -> list[User]:
        """Lista paginada de usuários, ordenada por id."""
        ...


class ProductRepository(Protocol):
    """Operações de persistência para produtos."""

    def get_by_id(self, product_id: int) -> Product | None:
        """Recupera o produto pelo id, ou None se inexistente."""
        ...

    def list(
        self, offset: int, limit: int, only_active: bool
    ) -> tuple[list[Product], int]:
        """Lista paginada de produtos, com o total para paginação."""
        ...

    def create(self, product: Product) -> Product:
        """Persiste um novo produto e devolve a instância recarregada."""
        ...

    def update(self, product: Product) -> Product:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        ...


class OrderRepository(Protocol):
    """Operações de persistência para pedidos."""

    def get_by_id(self, order_id: int) -> Order | None:
        """Recupera o pedido pelo id, ou None se inexistente."""
        ...

    def add(self, order: Order) -> Order:
        """Persiste um novo pedido e devolve a instância recarregada."""
        ...

    def update(self, order: Order) -> Order:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        ...

    def list_by_user(self, user_id: int, offset: int, limit: int) -> list[Order]:
        """Pedidos do usuário, do mais recente para o mais antigo."""
        ...


class PaymentRepository(Protocol):
    """Operações de persistência para pagamentos."""

    def create(self, payment: Payment) -> Payment:
        """Persiste um novo payment e devolve a instância recarregada."""
        ...

    def update(self, payment: Payment) -> Payment:
        """Efetiva alterações pendentes e devolve a instância recarregada."""
        ...

    def get_pending_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None:
        """Link ainda pendente do (pedido, provedor), ou None."""
        ...

    def get_by_order_and_provider(
        self, order_id: int, provider: str
    ) -> Payment | None:
        """Último payment registrado para o (pedido, provedor), ou None."""
        ...

    def get_by_provider_payment_link_id(self, link_id: str) -> Payment | None:
        """Payment vinculado ao id do link no gateway, ou None."""
        ...


__all__ = [
    "OrderRepository",
    "PaymentRepository",
    "ProductRepository",
    "UserRepository",
]
