"""Transaction CRUD routes (scoped by user)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate

router = APIRouter()


@router.get("/users/{user_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Transaction]:
    """List transactions for a user."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.post("/users/{user_id}/transactions", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    user_id: int,
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """Create a transaction for a user."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(by_alias=True)
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    transaction = Transaction(
        user_id=user_id,
        amount=payload.amount,
        currency=payload.currency,
        country=payload.country,
        status=payload.status,
        metadata_=data.get("metadata_"),
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)
    return transaction


@router.get("/users/{user_id}/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    user_id: int,
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """Get a transaction by ID for a user."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/users/{user_id}/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    user_id: int,
    transaction_id: int,
    payload: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Transaction:
    """Partially update a transaction."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    data = payload.model_dump(exclude_unset=True, by_alias=True)
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    for key, value in data.items():
        setattr(transaction, key, value)
    await db.flush()
    await db.refresh(transaction)
    return transaction


@router.delete("/users/{user_id}/transactions/{transaction_id}", status_code=204)
async def delete_transaction(
    user_id: int,
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a transaction."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(transaction)
    await db.flush()
