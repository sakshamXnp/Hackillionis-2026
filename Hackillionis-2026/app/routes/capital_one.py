"""Capital One Nessie API proxy + rule engine integration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.capital_one import (
    AccountSchema,
    CapitalOneTransactionSchema,
    CreateUserRequest,
    CreateUserResponse,
    CustomerSchema,
    EvaluatePurchaseRequest,
    EvaluatePurchaseResponse,
    EvaluationResponseSchema,
    TransactionWithEvaluationSchema,
    SeedRequest,
    SeedResponse,
    CustomerResponse,
    AccountResponse,
    CustomersListResponse,
    AccountsListResponse,
)
from app.schemas.evaluation import RuleResultSchema
from app.services.capital_one_client import CapitalOneClient
from app.services.rule_engine import create_default_engine

router = APIRouter()
_client = CapitalOneClient()
_engine = create_default_engine()


def _normalize_list(raw: list | dict) -> list[dict]:
    """Normalize API response to list of dicts."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "results" in raw:
        return raw["results"]
    if isinstance(raw, dict):
        return [raw]
    return []


def _to_evaluation_schema(transaction_id: int, risk_score: int, decision: str, rule_results: list) -> EvaluationResponseSchema:
    return EvaluationResponseSchema(
        transaction_id=transaction_id,
        risk_score=risk_score,
        decision=decision,
        rule_results=[
            {"rule_name": r.rule_name, "triggered": r.triggered, "message": r.message, "risk_contribution": r.risk_contribution}
            for r in rule_results
        ],
    )


@router.get("/customers", response_model=CustomersListResponse)
async def get_capital_one_customers() -> CustomersListResponse:
    """Fetch all customers from Capital One API."""
    try:
        raw = await _client.get_customers()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capital One API error: {e!s}") from e
    items = _normalize_list(raw) if isinstance(raw, (list, dict)) else []
    return CustomersListResponse(customers=[CustomerResponse.model_validate(x) for x in items])

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_capital_one_customer(customer_id: str) -> CustomerResponse:
    """Fetch a specific customer by ID from Capital One API."""
    try:
        raw = await _client.get_customer(customer_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Customer not found or API error: {e!s}") from e
    return CustomerResponse.model_validate(raw)


@router.get("/customers/{customer_id}/accounts", response_model=list[AccountResponse])
async def get_capital_one_customer_accounts(customer_id: str) -> list[AccountResponse]:
    """Fetch accounts for a specific customer from Capital One."""
    try:
        raw = await _client.get_customer_accounts(customer_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capital One API error: {e!s}") from e
    items = _normalize_list(raw) if isinstance(raw, (list, dict)) else []
    return [AccountResponse.model_validate(x) for x in items]

@router.get("/accounts", response_model=AccountsListResponse)
async def get_capital_one_accounts() -> AccountsListResponse:
    """Fetch all accounts from Capital One API."""
    try:
        raw = await _client.get_accounts()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capital One API error: {e!s}") from e
    items = _normalize_list(raw) if isinstance(raw, (list, dict)) else []
    return AccountsListResponse(accounts=[AccountResponse.model_validate(x) for x in items])

@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_capital_one_account(account_id: str) -> AccountResponse:
    """Fetch a specific account by ID from Capital One API."""
    try:
        raw = await _client.get_account(account_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Account not found or API error: {e!s}") from e
    return AccountResponse.model_validate(raw)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=list[TransactionWithEvaluationSchema],
)
async def get_account_transactions_with_evaluation(
    account_id: str,
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[TransactionWithEvaluationSchema]:
    """
    Fetch transactions from Capital One, then evaluate each with our RuleEngine.
    Requires user_id (query) to create local transactions and run rules.
    """
    # Ensure user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    try:
        raw = await _client.get_account_transactions(account_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capital One API error: {e!s}") from e
    items = _normalize_list(raw) if isinstance(raw, (list, dict)) else []
    out: list[TransactionWithEvaluationSchema] = []
    for tx_dict in items:
        amount = float(tx_dict.get("amount", 0) or 0)
        if amount <= 0:
            co_tx = CapitalOneTransactionSchema.model_validate(tx_dict)
            out.append(
                TransactionWithEvaluationSchema(
                    transaction=co_tx,
                    evaluation=EvaluationResponseSchema(
                        transaction_id=0,
                        risk_score=0,
                        decision="ALLOW",
                        rule_results=[],
                    ),
                )
            )
            continue
        # Create local transaction for evaluation
        local_tx = Transaction(
            user_id=user_id,
            amount=amount,
            currency="USD",
            country=tx_dict.get("country") or None,
            status="pending",
            metadata_=tx_dict,
        )
        db.add(local_tx)
        await db.flush()
        await db.refresh(local_tx)
        try:
            result = await _engine.evaluate_transaction(local_tx.id, db)
        except Exception:
            result = None
        eval_schema = _to_evaluation_schema(
            local_tx.id,
            result.risk_score if result else 0,
            result.decision if result else "ALLOW",
            result.rule_results if result else [],
        )
        out.append(
            TransactionWithEvaluationSchema(
                transaction=CapitalOneTransactionSchema.model_validate(tx_dict),
                evaluation=eval_schema,
            )
        )
    return out


@router.post(
    "/accounts/{account_id}/evaluate-purchase",
    response_model=EvaluatePurchaseResponse,
)
async def evaluate_purchase(
    account_id: str,
    payload: EvaluatePurchaseRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> EvaluatePurchaseResponse:
    """
    Create a purchase in Capital One API, create transaction in our DB,
    run rule engine evaluation. Returns Capital One response + evaluation.
    user_id (query) links the local transaction and rule config.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    try:
        co_response = await _client.create_purchase(
            account_id=account_id,
            amount=payload.amount,
            description=payload.description,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capital One API error: {e!s}") from e
    # Create local transaction
    local_tx = Transaction(
        user_id=user_id,
        amount=payload.amount,
        currency="USD",
        country=payload.country,
        status="pending",
        metadata_={"capital_one_response": co_response},
    )
    db.add(local_tx)
    await db.flush()
    await db.refresh(local_tx)
    try:
        result = await _engine.evaluate_transaction(local_tx.id, db)
    except Exception:
        result = None
    eval_schema = _to_evaluation_schema(
        local_tx.id,
        result.risk_score if result else 0,
        result.decision if result else "ALLOW",
        result.rule_results if result else [],
    )
    return EvaluatePurchaseResponse(
        capital_one_response=co_response if isinstance(co_response, dict) else {"result": co_response},
        evaluation=eval_schema,
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_capital_one_data(
    payload: SeedRequest,
) -> SeedResponse:
    """
    Creates a customer and an account in Capital One API for testing purposes.
    Use POST /create-user afterwards to create a local user linked to the customer.
    """
    try:
        # Create Customer
        customer_resp = await _client.create_customer(payload.customer.model_dump())
        customer_item = customer_resp.get("objectCreated", customer_resp)
        customer_id = customer_item.get("_id") or customer_item.get("id")
        if not customer_id:
            raise ValueError(f"Could not find customer ID in response: {customer_resp}")

        # Create Account
        account_resp = await _client.create_account(customer_id, payload.account.model_dump())
        account_item = account_resp.get("objectCreated", account_resp)
        account_id = account_item.get("_id") or account_item.get("id")
        if not account_id:
            raise ValueError(f"Could not find account ID in response: {account_resp}")

        return SeedResponse(customer_id=customer_id, account_id=account_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to seed data: {e!s}") from e


@router.post("/create-user", response_model=CreateUserResponse)
async def create_local_user(
    payload: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateUserResponse:
    """
    Create a local user in the database, optionally linked to a Capital One customer_id.
    """
    try:
        user = User(
            name=payload.name,
            email=payload.email,
            customer_id=payload.customer_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return CreateUserResponse(
            user_id=user.id,
            name=user.name,
            email=user.email,
            customer_id=user.customer_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {e!s}") from e

