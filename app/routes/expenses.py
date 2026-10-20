import asyncio
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import get_rate_service, get_repo
from app.repository import ExpenseRepository
from app.schemas import (
    ConvertedExpense,
    ExpenseCreate,
    ExpenseList,
    ExpenseRead,
    ExpenseUpdate,
    SummaryBreakdown,
    SummaryRead,
)
from app.services.rates import RateService

router = APIRouter(tags=["expenses"])

MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


@router.post(
    "/expenses",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an expense",
    responses={201: {"description": "Expense created"}},
)
def create_expense(
    body: ExpenseCreate,
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
) -> ExpenseRead:
    return repo.create(body)


@router.get(
    "/expenses",
    response_model=ExpenseList,
    summary="List expenses",
    description="Supports `page`, `limit`, and an optional exact `category` filter.",
)
def list_expenses(
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size, max 100")] = 20,
    category: Annotated[Optional[str], Query(max_length=50)] = None,
) -> ExpenseList:
    items, total = repo.list(page=page, limit=limit, category=category)
    return ExpenseList(items=items, page=page, limit=limit, total=total)


@router.get(
    "/expenses/{expense_id}",
    response_model=ExpenseRead,
    summary="Get one expense",
    responses={404: {"description": "Expense not found"}},
)
def get_expense(
    expense_id: UUID,
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
) -> ExpenseRead:
    return repo.get(expense_id)


@router.patch(
    "/expenses/{expense_id}",
    response_model=ExpenseRead,
    summary="Update an expense",
    responses={404: {"description": "Expense not found"}},
)
def update_expense(
    expense_id: UUID,
    body: ExpenseUpdate,
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
) -> ExpenseRead:
    return repo.update(expense_id, body)


@router.delete(
    "/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an expense",
    responses={204: {"description": "Deleted"}, 404: {"description": "Expense not found"}},
)
def delete_expense(
    expense_id: UUID,
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
) -> Response:
    repo.delete(expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/expenses/{expense_id}/converted",
    response_model=ConvertedExpense,
    summary="Convert one expense to another currency",
    description="Calls the exchange-rate provider. Timeouts return 504; provider errors return 502.",
    responses={
        400: {"description": "Unknown currency"},
        404: {"description": "Expense not found"},
        502: {"description": "Rate provider error"},
        504: {"description": "Rate provider timeout"},
    },
)
async def convert_expense(
    expense_id: UUID,
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
    rates: Annotated[RateService, Depends(get_rate_service)],
    to: Annotated[str, Query(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")],
) -> ConvertedExpense:
    expense = repo.get(expense_id)
    rate = await rates.get_rate(expense.currency, to)
    return ConvertedExpense(
        id=expense.id,
        description=expense.description,
        category=expense.category,
        original_amount=expense.amount,
        original_currency=expense.currency,
        converted_amount=_money(expense.amount * rate),
        target_currency=to,
        rate=rate,
    )


@router.get(
    "/summary",
    response_model=SummaryRead,
    summary="Sum all expenses in one currency",
    description=(
        "Converts each unique source currency in parallel with `asyncio.gather`. "
        "The rate for a currency is fetched only once."
    ),
    responses={
        400: {"description": "Unknown currency"},
        502: {"description": "Rate provider error"},
        504: {"description": "Rate provider timeout"},
    },
)
async def summary(
    repo: Annotated[ExpenseRepository, Depends(get_repo)],
    rates: Annotated[RateService, Depends(get_rate_service)],
    to: Annotated[str, Query(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")],
) -> SummaryRead:
    expenses = repo.all()
    unique_currencies = {expense.currency for expense in expenses}
    rate_list = await asyncio.gather(
        *[rates.get_rate(currency, to) for currency in unique_currencies]
    )
    rate_by_currency = dict(zip(unique_currencies, rate_list))

    grouped: dict[str, list] = defaultdict(list)
    for expense in expenses:
        grouped[expense.currency].append(expense)

    breakdown: list[SummaryBreakdown] = []
    total = Decimal("0")
    for currency, group in sorted(grouped.items()):
        original_total = sum((item.amount for item in group), Decimal("0"))
        converted_total = _money(original_total * rate_by_currency[currency])
        total += converted_total
        breakdown.append(
            SummaryBreakdown(
                currency=currency,
                count=len(group),
                original_total=original_total,
                converted_total=converted_total,
            )
        )

    return SummaryRead(
        target_currency=to,
        total=_money(total),
        expense_count=len(expenses),
        breakdown=breakdown,
    )
