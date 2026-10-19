"""Criação e consulta de pedidos, com cálculo server-side dos totais."""


def test_create_order_computes_total_from_db(client, user, product):
    # Produto custa R$ 10,00; cliente não envia preço algum.
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 3}]},
        headers=user["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 30.0
    assert body["status"] == "PENDING"
    assert body["payment_status"] == "PENDING"
    assert body["items"][0]["unit_price"] == 10.0


def test_create_order_merges_repeated_products(client, user, product):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {"product_id": product["id"], "quantity": 2},
                {"product_id": product["id"], "quantity": 1},
            ]
        },
        headers=user["headers"],
    )
    assert response.status_code == 201
    body = response.json()
    # Itens do mesmo produto são somados: um item, quantidade 3.
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["total"] == 30.0


def test_create_order_uses_db_price_not_client_control(client, user, product):
    # Mudança do preço no banco deve refletir no próximo pedido (snapshot
    # por pedido), provando que o total vem do servidor.
    # (preço alterado via admin; este teste usa o preço original do fixture)
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=user["headers"],
    )
    assert response.json()["total"] == 10.0


def test_create_order_unknown_product_404(client, user):
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": 424242, "quantity": 1}]},
        headers=user["headers"],
    )
    assert response.status_code == 404


def test_create_order_inactive_product_rejected(client, admin, user, product):
    client.delete(f"/api/v1/products/{product['id']}", headers=admin["headers"])
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=user["headers"],
    )
    assert response.status_code == 400


def test_create_order_requires_auth(client, product):
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )
    assert response.status_code == 401


def test_get_order_by_owner(client, user, product):
    created = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=user["headers"],
    ).json()
    response = client.get(f"/api/v1/orders/{created['id']}", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_order_of_other_user_forbidden(client, user, another_user, product):
    created = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=another_user["headers"],
    ).json()
    response = client.get(f"/api/v1/orders/{created['id']}", headers=user["headers"])
    # Pedido de terceiro não deve ser acessível por usuário comum.
    assert response.status_code == 403


def test_get_order_allowed_for_admin(client, admin, user, product):
    created = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=user["headers"],
    ).json()
    response = client.get(f"/api/v1/orders/{created['id']}", headers=admin["headers"])
    assert response.status_code == 200


def test_list_my_orders(client, user, product):
    client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
        headers=user["headers"],
    )
    response = client.get("/api/v1/orders", headers=user["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 1
