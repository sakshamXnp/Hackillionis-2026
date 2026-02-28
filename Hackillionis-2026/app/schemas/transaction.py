"""Transaction Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    """Base transaction schema with shared fields."""

    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    country: str | None = Field(default=None, min_length=2, max_length=3)
    status: str = Field(default="pending", max_length=50)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction (user_id from path)."""

    pass


class TransactionUpdate(BaseModel):
    """Schema for partial transaction update."""

    amount: float | None = Field(None, gt=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    country: str | None = Field(None, min_length=2, max_length=3)
    status: str | None = Field(None, max_length=50)
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")


class TransactionResponse(TransactionBase):
    """Schema for transaction response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    user_id: int
    created_at: datetime
