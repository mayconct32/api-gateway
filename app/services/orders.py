from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import OrderStatus
from app.models.order import Order, OrderItem
from app.models.user import User, UserRole
from app.repositories import interfaces
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.schemas.orders import OrderCreate, OrderRead
from app.schemas.products import cents_to_brl


class OrderService:
    """Criação e consulta de pedidos.

    Regra de integridade financeira: nome, preço e total nunca vem do
    cliente; são calculados no servidor a partir dos produtos no banco.
    """

    def __init__(self, db: Session) -> None:
        self.order_repository: interfaces.OrderRepository = OrderRepository(db)
        self.product_repository: interfaces.ProductRepository = ProductRepository(db)

    @staticmethod
    def _to_read(order: Order) -> OrderRead:
        items = [
            {
                "product_id": item.product_id,
                "quantity": int(item.quantity),
                "unit_price": cents_to_brl(int(item.unit_price_cents)),
            }
            for item in order.items
        ]
        return OrderRead.model_validate(
            {
                "id": order.id,
                "user_id": order.user_id,
                "status": order.status,
                "payment_status": order.payment_status,
                "total": cents_to_brl(int(order.total_cents)),
                "created_at": order.created_at,
                "items": items,
            }
        )

    def create(self, payload: OrderCreate, current_user: User) -> OrderRead:
        # Tentar resolver todos os produtos primeiro: se algum faltar,
        # nada é gravado (transação única, sem pedido parcial).
        product_ids = [item.product_id for item in payload.items]
        products = {
            product.id: product
            for product in (self.product_repository.get_by_id(pid) for pid in product_ids)
            if product is not None
        }

        # Agrupa itens repetidos de produto e valida cada um.
        quantities: dict[int, int] = {}
        for item in payload.items:
            product = products.get(item.product_id)
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"product {item.product_id} not found",
                )
            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"product {item.product_id} is not available",
                )
            quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity

        total_cents = 0
        order = Order(user_id=current_user.id, status=OrderStatus.PENDING.value, payment_status="PENDING")
        for product_id, quantity in quantities.items():
            product = products[product_id]
            # Preço do banco no momento da compra (snapshot).
            total_cents += int(product.price_cents) * quantity
            order.items.append(
                OrderItem(
                    product_id=product_id,
                    quantity=quantity,
                    unit_price_cents=int(product.price_cents),
                )
            )
        # Total servido em centavos, recalculado sempre no servidor.
        order.total_cents = total_cents

        created = self.order_repository.add(order)
        return self._to_read(created)

    def get_owned_order(self, order_id: int, current_user: User) -> Order:
        """Pedido pelo id, garantindo que só o dono (ou ADMIN) acesse."""
        order = self.order_repository.get_by_id(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="order not found",
            )
        # Controle de acesso: usuários comuns só veem os próprios pedidos;
        # ADMIN pode consultar qualquer pedido.
        if order.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="access denied",
            )
        return order

    def get(self, order_id: int, current_user: User) -> OrderRead:
        order = self.get_owned_order(order_id, current_user)
        return self._to_read(order)

    def list_mine(self, current_user: User, offset: int, limit: int) -> list[OrderRead]:
        """Histórico do usuário autenticado (não há listing de todos)."""
        orders = self.order_repository.list_by_user(current_user.id, offset, limit)
        return [self._to_read(order) for order in orders]


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(db)
