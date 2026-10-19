from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Os pedidos aceitam apenas (product_id, quantity): nome e preço do item
# são sempre resolvidos no servidor a partir do banco de produtos (o
# cliente nunca envia valores).


class OrderItemCreate(BaseModel):
    """Item aceito na criação de um pedido: apenas referência e quantidade."""

    product_id: int
    quantity: int = Field(ge=1, le=100)


class OrderItemRead(BaseModel):
    """Item de pedido devolvido na resposta, com preço unitário em reais."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: float


class OrderCreate(BaseModel):
    """Payload de criação de pedido."""

    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderRead(BaseModel):
    """Pedido devolvido nas respostas da API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    payment_status: str
    total: float
    created_at: datetime
    items: list[OrderItemRead]
