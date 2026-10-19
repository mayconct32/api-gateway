from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)

    def list(
        self, offset: int = 0, limit: int = 50, only_active: bool = True
    ) -> tuple[list[Product], int]:
        """Lista paginada de produtos com o total (para headers de paginação)."""
        statement = select(Product)
        if only_active:
            statement = statement.where(Product.is_active)
        total = self.db.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = self.db.scalars(
            statement.order_by(Product.id).offset(offset).limit(limit)
        )
        return list(rows), int(total or 0)

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.commit()
        self.db.refresh(product)
        return product
