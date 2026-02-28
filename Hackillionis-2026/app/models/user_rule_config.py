"""Per-user rule configuration for the Strategy-based rule engine."""

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserRuleConfig(Base):
    """
    Per-user limits and settings used by concrete rule strategies.

    One row per user; missing config falls back to defaults in the rule engine.
    """

    __tablename__ = "user_rule_configs"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_rule_config_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    max_transaction_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_transactions_per_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_spending_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    blocked_countries: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="rule_config")
