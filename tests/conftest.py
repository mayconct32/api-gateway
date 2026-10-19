"""Fixtures de teste.

Banco SQLite em memória por teste e provedores de pagamento fakes
injetados via dependency_overrides: nenhum teste chama a API real dos
gateways e nenhum dado toca disco.
"""

import json
import os

# Variáveis definidas antes de importar a aplicação: Settings usa
# cache, portanto a configuração dos testes precisa existir primeiro.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-32-bytes-long")
os.environ.setdefault("BASE_URL", "http://testserver")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models import Base
from app.enums import PaymentProviderEnum
from app.payment_providers import PaymentGatewayError
from app.dependencies import get_providers


class FakeProvider:
    """Provedor fake determinístico, satisfaz o protocolo PaymentLinkProvider.

    Guarda o estado por link id; os testes podem ajustar is_paid e o
    valor retornado em detalhes para simular divergências e fraude.
    """

    def __init__(self) -> None:
        self.create_calls = 0
        self.fetch_calls = 0
        self.details: dict[str, dict] = {}

    def create_payment_link(
        self,
        order_id: int,
        amount_cents: int,
        user_email: str,
        user_name: str,
    ) -> dict:
        self.create_calls += 1
        link_id = f"link-{self.create_calls}"
        self.details[link_id] = {
            "amount_cents": amount_cents,
            "currency": "BRL",
            "is_paid": False,
        }
        return {
            "payment_link": f"https://pay.example/{link_id}",
            "provider_payment_link_id": link_id,
        }

    def get_payment_details(self, payment_id: str) -> dict:
        self.fetch_calls += 1
        data = self.details[payment_id]
        return {
            "payment_id": payment_id,
            "amount_cents": data["amount_cents"],
            "currency": data["currency"],
            "status": "paid" if data["is_paid"] else "created",
            "is_paid": data["is_paid"],
            "raw_payment_id": f"raw-{payment_id}",
        }

    def set_paid(
        self,
        payment_id: str,
        amount_cents: int | None = None,
        currency: str = "BRL",
    ) -> None:
        data = self.details[payment_id]
        data["is_paid"] = True
        if amount_cents is not None:
            data["amount_cents"] = amount_cents
        data["currency"] = currency

    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict:
        # Assinatura fixa nos testes; qualquer outro valor é rejeitado,
        # exercitando o caminho 403 do webhook.
        if signature != "valid-signature":
            raise PaymentGatewayError("invalid webhook signature")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PaymentGatewayError("invalid webhook payload") from exc


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def fake_provider():
    return FakeProvider()


@pytest.fixture()
def client(db_engine, fake_provider):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    # Fakes respondem por ambos os provedores: os testes cobrem os dois
    # caminhos (stripe/razorpay) sem credenciais nem chamadas reais.
    app.dependency_overrides[get_providers] = lambda: {
        PaymentProviderEnum.STRIPE: fake_provider,
        PaymentProviderEnum.RAZORPAY: fake_provider,
    }
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def user(client):
    """Usuário comum já cadastrado; retorna (headers, dados)."""
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "Maria Silva",
            "email": "maria@example.com",
            "password": "s3cret-p4ss",
        },
    )
    assert response.status_code == 201, response.text
    token = _login(client, "maria@example.com", "s3cret-p4ss")
    return {"headers": {"Authorization": f"Bearer {token}"}, "id": response.json()["id"]}


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def another_user(client):
    """Segundo usuário, usado para validar isolamento entre contas."""
    response = client.post(
        "/api/v1/users",
        json={
            "full_name": "José Souza",
            "email": "jose@example.com",
            "password": "s3cret-p4ss",
        },
    )
    assert response.status_code == 201, response.text
    token = _login(client, "jose@example.com", "s3cret-p4ss")
    return {"headers": {"Authorization": f"Bearer {token}"}, "id": response.json()["id"]}


@pytest.fixture()
def admin(client, db_engine):
    """Usuário ADMIN criado direto na base (não há signup de admin)."""
    from app.models.user import User, UserRole
    from app.security import hash_password

    with Session(db_engine) as db:
        admin_user = User(
            full_name="Admin",
            email="admin@example.com",
            hashed_password=hash_password("s3cret-p4ss"),
            role=UserRole.ADMIN,
        )
        db.add(admin_user)
        db.commit()
        admin_id = admin_user.id

    token = _login(client, "admin@example.com", "s3cret-p4ss")
    return {"headers": {"Authorization": f"Bearer {token}"}, "id": admin_id}


@pytest.fixture()
def product(client, admin):
    """Produto ativo de R$ 10,00 (1000 centavos)."""
    response = client.post(
        "/api/v1/products",
        json={"name": "Teclado", "price": 10.0},
        headers=admin["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()
