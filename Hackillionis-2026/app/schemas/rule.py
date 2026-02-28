"""Rule Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RuleBase(BaseModel):
    """Base rule schema with shared fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    condition_expression: str = Field(..., description="Expression to evaluate (e.g. amount > 1000)")
    action_type: str = Field(..., max_length=100, description="Action when condition matches")
    priority: int = Field(default=0, ge=0, description="Evaluation priority (higher first)")
    is_active: bool = Field(default=True, description="Whether the rule is active")


class RuleCreate(RuleBase):
    """Schema for creating a rule."""

    pass


class RuleUpdate(BaseModel):
    """Schema for partial rule update."""

    name: str | None = Field(None, min_length=1, max_length=255)
    condition_expression: str | None = None
    action_type: str | None = Field(None, max_length=100)
    priority: int | None = Field(None, ge=0)
    is_active: bool | None = None


class RuleResponse(RuleBase):
    """Schema for rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
