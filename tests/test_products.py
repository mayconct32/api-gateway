"""CRUD de produtos com restrição administrativa."""


def test_create_product_requires_admin(client, user):
    response = client.post(
        "/api/v1/products",
        json={"name": "Mouse", "price": 5.0},
        headers=user["headers"],
    )
    # Operação administrativa: usuário comum não pode criar produto.
    assert response.status_code == 403


def test_create_product_requires_auth(client):
    response = client.post(
        "/api/v1/products",
        json={"name": "Mouse", "price": 5.0},
    )
    assert response.status_code == 401


def test_create_product_as_admin(client, admin):
    response = client.post(
        "/api/v1/products",
        json={"name": "Mouse", "description": "USB", "price": 29.9},
        headers=admin["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Mouse"
    # Conversão reais -> centavos deve ser exata (2990).
    assert body["price"] == 29.9
    assert body["is_active"] is True


def test_create_product_invalid_price(client, admin):
    response = client.post(
        "/api/v1/products",
        json={"name": "Grátis", "price": 0},
        headers=admin["headers"],
    )
    assert response.status_code == 422


def test_list_products_public_and_paginated(client, admin, product):
    client.post(
        "/api/v1/products", json={"name": "Monitor", "price": 500.0}, headers=admin["headers"]
    )
    response = client.get("/api/v1/products?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.headers["X-Total-Count"] == "2"


def test_get_product(client, product):
    response = client.get(f"/api/v1/products/{product['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == product["id"]


def test_get_missing_product_404(client):
    assert client.get("/api/v1/products/9999").status_code == 404


def test_update_product_as_admin(client, admin, product):
    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": 15.5, "name": "Teclado mech"},
        headers=admin["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 15.5
    assert body["name"] == "Teclado mech"


def test_update_product_forbidden_for_user(client, user, product):
    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": 1.0},
        headers=user["headers"],
    )
    assert response.status_code == 403


def test_delete_product_is_logical(client, admin, product):
    response = client.delete(
        f"/api/v1/products/{product['id']}", headers=admin["headers"]
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    # Produto desativado sai da listagem pública...
    listing = client.get("/api/v1/products").json()
    assert all(p["id"] != product["id"] for p in listing)
    # ...mas continua acessível por id (histórico de pedidos).
    assert client.get(f"/api/v1/products/{product['id']}").status_code == 200
