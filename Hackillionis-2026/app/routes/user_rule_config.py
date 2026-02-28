"""User rule config CRUD (per-user limits for Strategy rule engine)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.user_rule_config import UserRuleConfig
from app.schemas.user_rule_config import (
    UserRuleConfigCreate,
    UserRuleConfigResponse,
    UserRuleConfigUpdate,
)

router = APIRouter()


@router.get("/{user_id}/rules", response_model=UserRuleConfigResponse | None)
async def get_user_rules(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserRuleConfig | None:
    """Get rule config for a user. Returns 404 if user missing, null if config not set."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(select(UserRuleConfig).where(UserRuleConfig.user_id == user_id))
    return result.scalar_one_or_none()


@router.post("/{user_id}/rules", response_model=UserRuleConfigResponse)
async def create_or_update_user_rules(
    user_id: int,
    payload: UserRuleConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> UserRuleConfig:
    """Create or replace rule config for a user."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(select(UserRuleConfig).where(UserRuleConfig.user_id == user_id))
    existing = result.scalar_one_or_none()
    if existing:
        existing.max_transaction_amount = payload.max_transaction_amount
        existing.max_transactions_per_hour = payload.max_transactions_per_hour
        existing.monthly_spending_limit = payload.monthly_spending_limit
        existing.blocked_countries = payload.blocked_countries or []
        await db.flush()
        await db.refresh(existing)
        return existing
    config = UserRuleConfig(
        user_id=user_id,
        max_transaction_amount=payload.max_transaction_amount,
        max_transactions_per_hour=payload.max_transactions_per_hour,
        monthly_spending_limit=payload.monthly_spending_limit,
        blocked_countries=payload.blocked_countries or [],
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.patch("/{user_id}/rules", response_model=UserRuleConfigResponse)
async def update_user_rules(
    user_id: int,
    payload: UserRuleConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserRuleConfig:
    """Partially update rule config for a user. Creates config if missing."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(select(UserRuleConfig).where(UserRuleConfig.user_id == user_id))
    existing = result.scalar_one_or_none()
    if not existing:
        config = UserRuleConfig(
            user_id=user_id,
            max_transaction_amount=payload.max_transaction_amount,
            max_transactions_per_hour=payload.max_transactions_per_hour,
            monthly_spending_limit=payload.monthly_spending_limit,
            blocked_countries=payload.blocked_countries if payload.blocked_countries is not None else [],
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
        return config
    data = payload.model_dump(exclude_unset=True)
    if "blocked_countries" in data and data["blocked_countries"] is None:
        del data["blocked_countries"]
    for key, value in data.items():
        setattr(existing, key, value)
    await db.flush()
    await db.refresh(existing)
    return existing
