"""Aplicação FastAPI do e-commerce.

Monta os routers de usuários, produtos, pedidos e pagamentos e
inicializa o schema do banco na inicialização (contexto dev; para
produção, use migrações — ver README).
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.database import engine
from app.routers import orders, products, users
from app.payment_providers import build_payment_providers
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # create_all é idempotente: cria as tabelas apenas se não existirem.
    # Em produção, prefira migrações versionadas (ex.: Alembic).
    from app.models import Base

    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Payment E-commerce API",
        version="0.2.0",
        description=(
            "E-commerce com pedidos e pagamentos via Stripe e Razorpay. "
            "Autenticação Bearer JWT; valores sempre calculados no servidor."
        ),
        lifespan=lifespan,
    )
    app.include_router(users.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    return app


app = create_app()
