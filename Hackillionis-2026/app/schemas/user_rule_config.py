"""UserRuleConfig Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


class UserRuleConfigBase(BaseModel):
    """Base schema for per-user rule configuration."""

    max_transaction_amount: float | None = Field(None, gt=0)
    max_transactions_per_hour: int | None = Field(None, ge=0)
    monthly_spending_limit: float | None = Field(None, ge=0)
    blocked_countries: list[str] | None = Field(default_factory=list)


class UserRuleConfigCreate(UserRuleConfigBase):
    """Schema for creating user rule config (user_id from path)."""

    pass


class UserRuleConfigUpdate(BaseModel):
    """Schema for partial update of user rule config."""

    max_transaction_amount: float | None = Field(None, gt=0)
    max_transactions_per_hour: int | None = Field(None, ge=0)
    monthly_spending_limit: float | None = Field(None, ge=0)
    blocked_countries: list[str] | None = None


class UserRuleConfigResponse(UserRuleConfigBase):
    """Schema for user rule config response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
