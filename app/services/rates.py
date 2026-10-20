from __future__ import annotations

import time
from decimal import Decimal
from typing import Optional

import httpx

from app.config import Settings
from app.errors import RateAPIError, RateTimeoutError, UnknownCurrencyError

_cache: dict[tuple[str, str], tuple[Decimal, float]] = {}


class RateService:
    """Talks only to the exchange-rate provider. Nothing else belongs here."""

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def get_rate(self, base: str, target: str) -> Decimal:
        base = base.upper()
        target = target.upper()
        if base == target:
            return Decimal("1")

        cached = self._from_cache(base, target)
        if cached is not None:
            return cached

        url = f"{self._settings.rates_api_url.rstrip('/')}/latest"
        params = {"from": base, "to": target}
        timeout = httpx.Timeout(self._settings.rates_timeout_seconds)

        try:
            response = await self._client.get(url, params=params, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise RateTimeoutError("Exchange rate provider timed out") from exc
        except httpx.RequestError as exc:
            raise RateAPIError("Exchange rate provider is unavailable") from exc

        if response.status_code == 404:
            raise UnknownCurrencyError(f"Unknown currency pair {base}/{target}")
        if response.status_code >= 400:
            raise RateAPIError(
                f"Exchange rate provider returned HTTP {response.status_code}"
            )

        try:
            payload = response.json()
            rate = Decimal(str(payload["rates"][target]))
        except (ValueError, KeyError, TypeError, httpx.JSONDecodeError) as exc:
            raise RateAPIError("Exchange rate provider returned invalid data") from exc

        self._store_cache(base, target, rate)
        return rate

    def _from_cache(self, base: str, target: str) -> Optional[Decimal]:
        entry = _cache.get((base, target))
        if entry is None:
            return None
        rate, expires_at = entry
        if time.monotonic() >= expires_at:
            _cache.pop((base, target), None)
            return None
        return rate

    def _store_cache(self, base: str, target: str, rate: Decimal) -> None:
        ttl = self._settings.rate_cache_ttl_seconds
        if ttl <= 0:
            return
        _cache[(base, target)] = (rate, time.monotonic() + ttl)


def clear_rate_cache() -> None:
    _cache.clear()
