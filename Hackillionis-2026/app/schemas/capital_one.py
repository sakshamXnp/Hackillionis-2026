"""Pydantic v2 schemas for Capital One Nessie API and related requests/responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CustomerSchema(BaseModel):
    """Capital One customer (Nessie API)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., alias="_id")
    first_name: str
    last_name: str
    email: str | None = None


class AccountSchema(BaseModel):
    """Capital One account (Nessie API)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., alias="_id")
    type: str
    nickname: str
    balance: float


class CapitalOneTransactionSchema(BaseModel):
    """Single transaction from Capital One API."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(..., alias="_id")
    amount: float
    description: str
    date: str = Field(..., alias="payment_date")


class EvaluatePurchaseRequest(BaseModel):
    """Request body for evaluate-purchase endpoint."""

    model_config = ConfigDict(from_attributes=True)

    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    country: str = "US"


class EvaluationResponseSchema(BaseModel):
    """Rule engine evaluation result for Capital One routes."""

    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    risk_score: int
    decision: str
    rule_results: list[dict] = Field(default_factory=list)


class TransactionWithEvaluationSchema(BaseModel):
    """Capital One transaction plus our RuleEngine evaluation result."""

    model_config = ConfigDict(from_attributes=True)

    transaction: CapitalOneTransactionSchema
    evaluation: EvaluationResponseSchema


class EvaluatePurchaseResponse(BaseModel):
    """Response: Capital One purchase response + our evaluation."""

    model_config = ConfigDict(from_attributes=True)

    capital_one_response: dict = Field(...)
    evaluation: EvaluationResponseSchema = Field(...)


class AddressSchema(BaseModel):
    """Address for Capital One Customer."""
    street_number: str
    street_name: str
    city: str
    state: str
    zip: str


class CustomerSeedSchema(BaseModel):
    """Customer creation data."""
    first_name: str
    last_name: str
    address: AddressSchema


class AccountSeedSchema(BaseModel):
    """Account creation data."""
    type: str = Field(..., description="'Credit Card' or 'Savings' or 'Checking'")
    nickname: str
    rewards: int = 0
    balance: int = 0


class SeedRequest(BaseModel):
    """Request payload for /capital-one/seed endpoint."""
    customer: CustomerSeedSchema
    account: AccountSeedSchema


class SeedResponse(BaseModel):
    """Response payload for /capital-one/seed endpoint."""
    customer_id: str
    account_id: str
    user_id: int | None = None


class CreateUserRequest(BaseModel):
    """Request payload for creating a local user."""
    name: str
    email: str
    customer_id: str | None = None


class CreateUserResponse(BaseModel):
    """Response payload for creating a local user."""
    user_id: int
    name: str
    email: str
    customer_id: str | None = None


class CustomerResponse(CustomerSchema):
    """Matches Nessie customer format."""
    address: AddressSchema | None = None


class AccountResponse(AccountSchema):
    """Matches Nessie account format."""
    customer_id: str | None = None


class CustomersListResponse(BaseModel):
    """List of customers."""
    customers: list[CustomerResponse]


class AccountsListResponse(BaseModel):
    """List of accounts."""
    accounts: list[AccountResponse]
