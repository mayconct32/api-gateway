"""Dependências do FastAPI (composition root da aplicação).

Este módulo concentra o acoplamento declarado ao framework: unicidade
de sessão por request, construção dos serviços e resolução do usuário
autenticado. As regras de negócio ficam em app/services sem conhecer
FastAPI; os routers apenas declaram o que precisam via Depends.
"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import PaymentProviderEnum
from app.exceptions import AccessDeniedError
from app.models.user import User, UserRole
from app.payment_providers import PaymentLinkProvider
from app.services.orders import OrderService
from app.services.payments import PaymentService
from app.services.products import ProductService
from app.services.users import UserService

# O token chega como Bearer no header Authorization; o endpoint de
# login correspondente é o /api/v1/auth/token (OAuth2PasswordBearer).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Constrói o UserService com a sessão do request."""
    return UserService(db)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Constrói o ProductService com a sessão do request."""
    return ProductService(db)


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Constrói o OrderService com a sessão do request."""
    return OrderService(db)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Usuário autenticado a partir do token Bearer do request."""
    return UserService(db).require_user(token)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige papel ADMIN; recusa usuários comuns nas rotas administrativas."""
    if current_user.role != UserRole.ADMIN:
        raise AccessDeniedError("admin access required")
    return current_user


def get_providers() -> dict[PaymentProviderEnum, PaymentLinkProvider]:
    """Provedores de pagamento com credenciais configuradas.

    Função isolada para ser sobrescrita nos testes com fakes, sem tocar
    em código de produção ou chamar APIs reais dos gateways.
    """
    from app.config import get_settings
    from app.payment_providers import build_payment_providers

    return build_payment_providers(get_settings())


def build_payment_service(
    db: Session = Depends(get_db),
    providers: dict[PaymentProviderEnum, PaymentLinkProvider] = Depends(get_providers),
) -> PaymentService:
    """Constrói o PaymentService com a sessão e os provedores do request."""
    return PaymentService(db, providers)
