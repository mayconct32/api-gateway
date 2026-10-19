from app.models.base import Base

# Importa os modelos no __init__ do pacote: garante que todas as tabelas
# estejam registradas em Base.metadata antes de qualquer create_all.
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.payment import Payment

__all__ = ["Base", "User", "Product", "Order", "OrderItem", "Payment"]
