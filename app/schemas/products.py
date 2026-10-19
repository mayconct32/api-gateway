from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Conversão entre reais e centavos fica explícita nos schemas de entrada
# e saída: a API aceita preços em reais (float), o banco e os gateways
# trabalham com centavos (int). Formato BRL.


def brl_to_cents(price: float) -> int:
    """Converte reais em centavos, protegendo de erros de ponto flutuante."""
    return int(round(price * 100))


def cents_to_brl(cents: int) -> float:
    """Converte centavos em reais para apresentação na API."""
    return cents / 100


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    # Preço informado em reais (ex.: 19.90); convertido para centavos.
    price: float = Field(gt=0, le=100_000)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, gt=0, le=100_000)
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: float
    is_active: bool
    created_at: datetime
