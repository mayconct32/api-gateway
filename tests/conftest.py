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
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
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
