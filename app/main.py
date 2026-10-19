"""Aplicação FastAPI do e-commerce.

Monta os routers de usuários, produtos, pedidos e pagamentos e
inicializa o schema do banco na inicialização (contexto dev; para
produção, use migrações — ver README).
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.database import engine
from app.error_handlers import register_exception_handlers
from app.routers import orders, payments, products, users, webhooks


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
    register_exception_handlers(app)
    app.include_router(users.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
