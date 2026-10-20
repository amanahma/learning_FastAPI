from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.repository import ExpenseRepository
from app.services.rates import RateService


def get_repo(request: Request) -> ExpenseRepository:
    return request.app.state.repo


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_rate_service(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RateService:
    return RateService(client, settings)
