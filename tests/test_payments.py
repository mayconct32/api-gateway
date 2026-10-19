"""Fluxo completo de pagamentos: link, idempotência, verificação e webhooks.

Os provedores são fakes (conftest), mas as regras do serviço —
idempotência, validação de valor, transições de estado, assinatura do
webhook — são as mesmas do código de produção.
"""

import json


def _create_order(client, user, product, quantity=1):
    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product["id"], "quantity": quantity}]},
        headers=user["headers"],
    )
    assert response.status_code == 201
    return response.json()


def test_create_payment_link(client, user, product, fake_provider):
    order = _create_order(client, user, product, quantity=2)
    response = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=user["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stripe"
    assert body["amount"] == 20.0
    assert body["currency"] == "BRL"
    assert body["payment_link"].startswith("https://pay.example/")
    assert fake_provider.create_calls == 1


def test_create_payment_link_is_idempotent(client, user, product, fake_provider):
    order = _create_order(client, user, product)
    payload = {"order_id": order["id"], "provider": "stripe"}
    first = client.post("/api/v1/payments/create-link", json=payload, headers=user["headers"]).json()
    second = client.post("/api/v1/payments/create-link", json=payload, headers=user["headers"]).json()
    # Segunda chamada reutiliza o link pendente: gateway é acionado uma
    # única vez (evita cobranças duplicadas).
    assert first["provider_payment_link_id"] == second["provider_payment_link_id"]
    assert fake_provider.create_calls == 1


def test_create_payment_link_for_other_user_order(client, user, another_user, product):
    order = _create_order(client, user, product)
    response = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=another_user["headers"],
    )
    assert response.status_code == 403


def _pay_order(client, user, product):
    order = _create_order(client, user, product)
    link = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=user["headers"],
    ).json()
    link_id = link["provider_payment_link_id"]
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": link_id,
                "amount_total": 1000,
                "currency": "brl",
                "payment_status": "paid",
            }
        },
    }
    response = client.post(
        "/api/v1/payments/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "valid-signature"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    return order, link_id


def test_webhook_marks_order_paid(client, user, product):
    order, _ = _pay_order(client, user, product)
    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=user["headers"]).json()
    assert fetched["payment_status"] == "PAID"
    assert fetched["status"] == "CONFIRMED"


def test_webhook_is_idempotent_on_repeated_events(client, user, product):
    order, link_id = _pay_order(client, user, product)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": link_id,
                "amount_total": 1000,
                "currency": "brl",
                "payment_status": "paid",
            }
        },
    }
    response = client.post(
        "/api/v1/payments/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "valid-signature"},
    )
    # Evento repetido (replay) não deve alterar o estado novamente.
    assert response.json()["status"] == "already_processed"
    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=user["headers"]).json()
    assert fetched["payment_status"] == "PAID"


def test_webhook_rejects_invalid_signature(client, user, product):
    order = _create_order(client, user, product)
    client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=user["headers"],
    )
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "link-1", "amount_total": 1000, "payment_status": "paid"}},
    }
    response = client.post(
        "/api/v1/payments/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "forged-signature"},
    )
    assert response.status_code == 403


def test_webhook_amount_mismatch_does_not_pay(client, user, product):
    order = _create_order(client, user, product)
    link = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=user["headers"],
    ).json()
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": link["provider_payment_link_id"],
                "amount_total": 1,  # divergente do valor registrado
                "currency": "brl",
                "payment_status": "paid",
            }
        },
    }
    response = client.post(
        "/api/v1/payments/webhooks/stripe",
        content=json.dumps(event),
        headers={"stripe-signature": "valid-signature"},
    )
    assert response.json()["status"] == "amount_mismatch"
    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=user["headers"]).json()
    assert fetched["payment_status"] == "PENDING"


def test_razorpay_webhook_flow(client, user, product):
    order = _create_order(client, user, product)
    link = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "razorpay"},
        headers=user["headers"],
    ).json()
    event = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": link["provider_payment_link_id"],
                    "amount": 1000,
                    "currency": "BRL",
                }
            }
        },
    }
    response = client.post(
        "/api/v1/payments/webhooks/razorpay",
        content=json.dumps(event),
        headers={"x-razorpay-signature": "valid-signature"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=user["headers"]).json()
    assert fetched["payment_status"] == "PAID"


def test_verify_payment_confirms_and_is_idempotent(client, user, product, fake_provider):
    order, link_id = _pay_order(client, user, product)
    fake_provider.set_paid(link_id)
    payload = {
        "order_id": order["id"],
        "provider": "stripe",
        "payment_id": link_id,
    }
    response = client.post("/api/v1/payments/verify", json=payload, headers=user["headers"])
    assert response.status_code == 200
    body = response.json()
    assert body["payment_status"] == "PAID"
    assert body["order_status"] == "CONFIRMED"

    # Segunda verificação não consulta o gateway novamente (idempotência).
    fetches_before = fake_provider.fetch_calls
    second = client.post("/api/v1/payments/verify", json=payload, headers=user["headers"])
    assert second.status_code == 200
    assert fake_provider.fetch_calls == fetches_before


def test_verify_payment_gateway_fetch(client, user, product, fake_provider):
    """Verificação via endpoint quando o webhook não chegou ainda."""
    order = _create_order(client, user, product)
    link = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "stripe"},
        headers=user["headers"],
    ).json()
    fake_provider.set_paid(link["provider_payment_link_id"])
    response = client.post(
        "/api/v1/payments/verify",
        json={
            "order_id": order["id"],
            "provider": "stripe",
            "payment_id": link["provider_payment_link_id"],
        },
        headers=user["headers"],
    )
    assert response.status_code == 200
    assert response.json()["payment_status"] == "PAID"
    fetched = client.get(f"/api/v1/orders/{order['id']}", headers=user["headers"]).json()
    assert fetched["status"] == "CONFIRMED"


def test_create_link_after_order_paid_rejected(client, user, product, fake_provider):
    order, _ = _pay_order(client, user, product)
    response = client.post(
        "/api/v1/payments/create-link",
        json={"order_id": order["id"], "provider": "razorpay"},
        headers=user["headers"],
    )
    # Pedido pago não abre nova tentativa de pagamento (evita dupla
    # cobrança do mesmo pedido).
    assert response.status_code == 400


def test_verify_unknown_payment_404(client, user, product):
    order = _create_order(client, user, product)
    response = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order["id"], "provider": "stripe", "payment_id": "cs_missing"},
        headers=user["headers"],
    )
    assert response.status_code == 404
