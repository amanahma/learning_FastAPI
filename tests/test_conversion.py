from decimal import Decimal

from app.deps import get_rate_service
from app.main import app
from tests.conftest import FailingRateService, TimeoutRateService


def _create_eur(client):
    return client.post(
        "/expenses",
        json={"amount": "50.00", "currency": "EUR", "description": "lunch", "category": "food"},
    ).json()


def test_convert_success(client):
    expense = _create_eur(client)
    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "INR"})
    assert response.status_code == 200
    body = response.json()
    assert body["original_amount"] == "50.00"
    assert body["original_currency"] == "EUR"
    assert body["target_currency"] == "INR"
    assert body["converted_amount"] == "4500.00"
    assert body["rate"] == "90"


def test_convert_timeout_returns_504(client):
    expense = _create_eur(client)
    app.dependency_overrides[get_rate_service] = lambda: TimeoutRateService()
    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "INR"})
    assert response.status_code == 504
    assert response.json()["error"] == "rate_timeout"


def test_convert_provider_failure_returns_502(client):
    expense = _create_eur(client)
    app.dependency_overrides[get_rate_service] = lambda: FailingRateService()
    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "INR"})
    assert response.status_code == 502
    assert response.json()["error"] == "rate_provider_error"


def test_convert_unknown_currency_returns_400(client):
    expense = _create_eur(client)
    response = client.get(f"/expenses/{expense['id']}/converted", params={"to": "XXX"})
    assert response.status_code == 400
    assert response.json()["error"] == "unknown_currency"


def test_summary_uses_fake_rates(client):
    client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "EUR", "description": "lunch"},
    )
    client.post(
        "/expenses",
        json={"amount": "10.00", "currency": "USD", "description": "snack"},
    )
    response = client.get("/summary", params={"to": "INR"})
    assert response.status_code == 200
    body = response.json()
    # 10 EUR * 90 + 10 USD * 83 = 1730
    assert Decimal(body["total"]) == Decimal("1730.00")
    assert body["expense_count"] == 2
    assert body["target_currency"] == "INR"
    currencies = {row["currency"] for row in body["breakdown"]}
    assert currencies == {"EUR", "USD"}


def test_unhandled_error_hides_traceback(client):
    from app.deps import get_repo

    def exploding_repo():
        raise RuntimeError("do not show this")

    app.dependency_overrides[get_repo] = exploding_repo
    response = client.get("/expenses")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error"
    assert body["detail"] == "An unexpected error occurred."
    assert "do not show this" not in str(body)
    assert "Traceback" not in str(body)
