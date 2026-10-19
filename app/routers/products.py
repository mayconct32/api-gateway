from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_current_admin, get_product_service
from app.models.user import User
from app.schemas.products import ProductCreate, ProductRead, ProductUpdate
from app.services.products import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    admin: User = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Cadastro de produto (ADMIN); clientes não podem criar produtos."""
    return service.create(payload)


@router.get("", response_model=list[ProductRead])
def list_products(
    response: Response,
    skip: int = 0,
    limit: int = 50,
    service: ProductService = Depends(get_product_service),
) -> list[ProductRead]:
    """Listagem pública paginada de produtos ativos.

    O total de itens volta no header X-Total-Count, que permite ao
    cliente paginar sem expor estruturas internas da API.
    """
    products, total = service.list(skip, limit)
    response.headers["X-Total-Count"] = str(total)
    return products


@router.get("/{product_id}", response_model=ProductRead)
def read_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Consulta pública de um produto ativo."""
    return service.get(product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    admin: User = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Atualização de produto (ADMIN)."""
    return service.update(product_id, payload)


@router.delete("/{product_id}", response_model=ProductRead)
def delete_product(
    product_id: int,
    admin: User = Depends(get_current_admin),
    service: ProductService = Depends(get_product_service),
) -> ProductRead:
    """Exclusão lógica de produto (ADMIN): marca is_active=False.

    Histórico de pedidos mantém referência ao produto, então a
    exclusão física é evitada de propósito (integridade referencial).
    """
    return service.deactivate(product_id)
