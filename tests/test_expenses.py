from uuid import uuid4


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


def test_create_expense_success(client):
    response = client.post(
        "/expenses",
        json={
            "amount": "50.00",
            "currency": "EUR",
            "description": "lunch",
            "category": "food",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "50.00"
    assert body["currency"] == "EUR"
    assert body["description"] == "lunch"
    assert "id" in body
    assert set(body) == {
        "id",
        "amount",
        "currency",
        "description",
        "category",
        "created_at",
        "updated_at",
    }


def test_create_bad_amount_returns_422(client):
    response = client.post(
        "/expenses",
        json={"amount": 0, "currency": "EUR", "description": "lunch"},
    )
    assert response.status_code == 422


def test_create_bad_currency_returns_422(client):
    response = client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "euro", "description": "lunch"},
    )
    assert response.status_code == 422


def test_get_expense_success(client):
    created = client.post(
        "/expenses",
        json={"amount": "8.50", "currency": "USD", "description": "coffee"},
    ).json()
    response = client.get(f"/expenses/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_expense_not_found(client):
    response = client.get(f"/expenses/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert "detail" in body
    assert "request_id" in body
    assert "traceback" not in body
    assert "Traceback" not in str(body)


def test_list_expenses_filters_by_category(client):
    client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "EUR", "description": "lunch", "category": "food"},
    )
    client.post(
        "/expenses",
        json={"amount": "20.00", "currency": "EUR", "description": "metro", "category": "travel"},
    )
    response = client.get("/expenses", params={"category": "food", "page": 1, "limit": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "food"


def test_update_expense_success(client):
    created = client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "EUR", "description": "lunch"},
    ).json()
    response = client.patch(
        f"/expenses/{created['id']}",
        json={"description": "dinner"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "dinner"
    assert response.json()["amount"] == "10.00"


def test_update_expense_not_found(client):
    response = client.patch(f"/expenses/{uuid4()}", json={"description": "x"})
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_delete_expense_success(client):
    created = client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "EUR", "description": "lunch"},
    ).json()
    response = client.delete(f"/expenses/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/expenses/{created['id']}").status_code == 404


def test_delete_expense_not_found(client):
    response = client.delete(f"/expenses/{uuid4()}")
    assert response.status_code == 404
