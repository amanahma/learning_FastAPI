from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


CURRENCY_PATTERN = r"^[A-Z]{3}$"


class ExpenseCreate(BaseModel):
    """Body for creating an expense."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "amount": "50.00",
                    "currency": "EUR",
                    "description": "lunch",
                    "category": "food",
                }
            ]
        }
    )

    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Must be greater than 0")
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=CURRENCY_PATTERN,
        description="ISO 4217 code, exactly 3 uppercase letters",
        examples=["EUR"],
    )
    description: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)


class ExpenseUpdate(BaseModel):
    """Body for a partial update. Omit fields you do not want to change."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "amount": "12.50",
                    "description": "coffee",
                }
            ]
        }
    )

    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern=CURRENCY_PATTERN,
    )
    description: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)


class ExpenseRead(BaseModel):
    """Public expense representation. No internal storage fields leak here."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "amount": "50.00",
                    "currency": "EUR",
                    "description": "lunch",
                    "category": "food",
                    "created_at": "2026-10-20T12:00:00Z",
                    "updated_at": "2026-10-20T12:00:00Z",
                }
            ]
        }
    )

    id: UUID
    amount: Decimal
    currency: str
    description: str
    category: Optional[str]
    created_at: datetime
    updated_at: datetime


class ExpenseList(BaseModel):
    items: list[ExpenseRead]
    page: int
    limit: int
    total: int


class ConvertedExpense(BaseModel):
    id: UUID
    description: str
    category: Optional[str]
    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    target_currency: str
    rate: Decimal


class SummaryBreakdown(BaseModel):
    currency: str
    count: int
    original_total: Decimal
    converted_total: Decimal


class SummaryRead(BaseModel):
    target_currency: str
    total: Decimal
    expense_count: int
    breakdown: list[SummaryBreakdown]


class HealthRead(BaseModel):
    status: str = "ok"


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str
