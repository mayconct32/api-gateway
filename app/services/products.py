from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.repositories import interfaces
from app.repositories.products import ProductRepository
from app.schemas.products import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    brl_to_cents,
    cents_to_brl,
)


class ProductService:
    """CRUD de produtos; valores monetários sempre regularizados em centavos."""

    def __init__(self, db: Session) -> None:
        self.repository: interfaces.ProductRepository = ProductRepository(db)

    def _to_read(self, product: Product) -> ProductRead:
        data = {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": cents_to_brl(int(product.price_cents)),
            "is_active": product.is_active,
            "created_at": product.created_at,
        }
        return ProductRead.model_validate(data)

    def create(self, payload: ProductCreate) -> ProductRead:
        product = self.repository.create(
            Product(
                name=payload.name,
                description=payload.description,
                # Preço convertido para centavos no servidor.
                price_cents=brl_to_cents(payload.price),
                is_active=True,
            )
        )
        return self._to_read(product)

    def get(self, product_id: int) -> ProductRead:
        product = self.repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        return self._to_read(product)

    def list(self, offset: int, limit: int) -> tuple[list[ProductRead], int]:
        products, total = self.repository.list(offset, limit)
        return [self._to_read(p) for p in products], total

    def update(self, product_id: int, payload: ProductUpdate) -> ProductRead:
        product = self.repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        if payload.name is not None:
            product.name = payload.name
        if payload.description is not None:
            product.description = payload.description
        if payload.price is not None:
            product.price_cents = brl_to_cents(payload.price)
        if payload.is_active is not None:
            product.is_active = payload.is_active
        self.repository.update(product)
        return self._to_read(product)

    def deactivate(self, product_id: int) -> ProductRead:
        """Exclusão lógica: mantém histórico de pedidos consistente."""
        product = self.repository.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
        # Sem verificação de estado: desativar é idempotente.
        product.is_active = False
        self.repository.update(product)
        return self._to_read(product)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)
