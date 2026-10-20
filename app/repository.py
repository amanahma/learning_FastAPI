from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Protocol
from uuid import UUID, uuid4

from app.errors import NotFoundError
from app.schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExpenseRepository(Protocol):
    def create(self, data: ExpenseCreate) -> ExpenseRead: ...

    def list(
        self,
        page: int,
        limit: int,
        category: Optional[str] = None,
    ) -> tuple[list[ExpenseRead], int]: ...

    def get(self, expense_id: UUID) -> ExpenseRead: ...

    def update(self, expense_id: UUID, data: ExpenseUpdate) -> ExpenseRead: ...

    def delete(self, expense_id: UUID) -> None: ...

    def all(self) -> list[ExpenseRead]: ...


class InMemoryExpenseRepository:
    """Dict-backed store. Swap this class in M0.4 without touching routes."""

    def __init__(self) -> None:
        self._items: dict[UUID, ExpenseRead] = {}

    def create(self, data: ExpenseCreate) -> ExpenseRead:
        now = _utcnow()
        expense = ExpenseRead(
            id=uuid4(),
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            category=data.category,
            created_at=now,
            updated_at=now,
        )
        self._items[expense.id] = expense
        return expense

    def list(
        self,
        page: int,
        limit: int,
        category: Optional[str] = None,
    ) -> tuple[list[ExpenseRead], int]:
        items = list(self._items.values())
        if category is not None:
            items = [item for item in items if item.category == category]
        items.sort(key=lambda item: item.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * limit
        return items[start : start + limit], total

    def get(self, expense_id: UUID) -> ExpenseRead:
        expense = self._items.get(expense_id)
        if expense is None:
            raise NotFoundError(f"Expense {expense_id} not found")
        return expense

    def update(self, expense_id: UUID, data: ExpenseUpdate) -> ExpenseRead:
        current = self.get(expense_id)
        updates = data.model_dump(exclude_unset=True)
        updated = current.model_copy(update={**updates, "updated_at": _utcnow()})
        self._items[expense_id] = updated
        return updated

    def delete(self, expense_id: UUID) -> None:
        self.get(expense_id)
        del self._items[expense_id]

    def all(self) -> list[ExpenseRead]:
        return list(self._items.values())
