from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user, get_order_service
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderRead
from app.services.orders import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    """Criação de pedido para o usuário autenticado.

    Somente product_id e quantity vêm do cliente: valores e totais são
    sempre calculados no servidor a partir dos preços do banco.
    """
    return service.create(payload, current_user)


@router.get("", response_model=list[OrderRead])
def list_my_orders(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> list[OrderRead]:
    """Histórico de pedidos do usuário autenticado."""
    return service.list_mine(current_user, skip, limit)


@router.get("/{order_id}", response_model=OrderRead)
def read_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    """Consulta de pedido; apenas o dono (ou ADMIN) tem acesso."""
    return service.get(order_id, current_user)
