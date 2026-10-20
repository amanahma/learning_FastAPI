from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.deps import get_rate_service, get_repo
from app.errors import RateAPIError, RateTimeoutError, UnknownCurrencyError
from app.main import app
from app.repository import InMemoryExpenseRepository
from app.services.rates import clear_rate_cache


class FakeRateService:
    def __init__(self, rates: dict[tuple[str, str], Decimal] | None = None) -> None:
        self.rates = rates or {("EUR", "INR"): Decimal("90"), ("USD", "INR"): Decimal("83")}

    async def get_rate(self, base: str, target: str) -> Decimal:
        base, target = base.upper(), target.upper()
        if base == target:
            return Decimal("1")
        try:
            return self.rates[(base, target)]
        except KeyError as exc:
            raise UnknownCurrencyError(f"Unknown currency pair {base}/{target}") from exc


class TimeoutRateService:
    async def get_rate(self, base: str, target: str) -> Decimal:
        raise RateTimeoutError("Exchange rate provider timed out")


class FailingRateService:
    async def get_rate(self, base: str, target: str) -> Decimal:
        raise RateAPIError("Exchange rate provider is unavailable")


@pytest.fixture
def repo() -> InMemoryExpenseRepository:
    return InMemoryExpenseRepository()


@pytest.fixture
def rates() -> FakeRateService:
    return FakeRateService()


@pytest.fixture
def client(repo: InMemoryExpenseRepository, rates: FakeRateService):
    clear_rate_cache()
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_rate_service] = lambda: rates
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_rate_cache()
