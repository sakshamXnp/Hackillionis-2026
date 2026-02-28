"""
Strategy-pattern rule engine: abstract BaseRule, concrete strategies,
and RuleEngine that evaluates a transaction by transaction_id using per-user RuleConfig.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.user_rule_config import UserRuleConfig

if TYPE_CHECKING:
    from app.models.user import User


@dataclass
class UserRulesView:
    """
    In-memory view of per-user rule config for strategy evaluate().
    Built from UserRuleConfig row or defaults when missing.
    """

    max_transaction_amount: float | None  # None = no limit
    max_transactions_per_hour: int | None  # None = no limit
    monthly_spending_limit: float | None  # None = no limit
    blocked_countries: list[str]  # empty = none blocked


# Sentinel for "no limit" so we can distinguish 0 from unset
def _default_user_rules() -> UserRulesView:
    return UserRulesView(
        max_transaction_amount=None,
        max_transactions_per_hour=None,
        monthly_spending_limit=None,
        blocked_countries=[],
    )


@dataclass
class RuleResult:
    """Result of a single rule evaluation."""

    triggered: bool
    message: str
    risk_contribution: int  # 0-100 from rule weight when triggered
    rule_name: str = ""  # set by engine for API responses


@dataclass
class EvaluationResult:
    """Aggregate result of evaluating all registered rules for a transaction."""

    transaction_id: int
    risk_score: int  # sum of risk_contribution for triggered rules, capped at 100
    decision: Literal["ALLOW", "REVIEW", "BLOCK"]
    rule_results: list[RuleResult] = field(default_factory=list)


def _decision_from_score(risk_score: int) -> Literal["ALLOW", "REVIEW", "BLOCK"]:
    """ALLOW if score < 40, REVIEW if 40-70, BLOCK if > 70."""
    if risk_score < 40:
        return "ALLOW"
    if risk_score <= 70:
        return "REVIEW"
    return "BLOCK"


class BaseRule(ABC):
    """Abstract base for all rule strategies."""

    def __init__(self, name: str, weight: int) -> None:
        if not 0 <= weight <= 100:
            raise ValueError("weight must be between 0 and 100")
        self.name = name
        self.weight = weight

    @abstractmethod
    async def evaluate(
        self,
        transaction: Transaction,
        user_rules: UserRulesView,
        db: AsyncSession,
    ) -> RuleResult:
        """Evaluate this rule; return RuleResult (triggered=True when rule is violated)."""
        ...


class MaxAmountRule(BaseRule):
    """Triggers when transaction.amount > user_rules.max_transaction_amount."""

    def __init__(self, weight: int = 30) -> None:
        super().__init__(name="MaxAmountRule", weight=weight)

    async def evaluate(
        self,
        transaction: Transaction,
        user_rules: UserRulesView,
        db: AsyncSession,
    ) -> RuleResult:
        limit = user_rules.max_transaction_amount
        if limit is None:
            return RuleResult(triggered=False, message="No amount limit set", risk_contribution=0)
        if transaction.amount <= limit:
            return RuleResult(
                triggered=False,
                message=f"Amount {transaction.amount} within limit {limit}",
                risk_contribution=0,
            )
        return RuleResult(
            triggered=True,
            message=f"Amount {transaction.amount} exceeds limit {limit}",
            risk_contribution=self.weight,
        )


class VelocityRule(BaseRule):
    """Triggers when count of user transactions in the last hour >= max_transactions_per_hour."""

    def __init__(self, weight: int = 25) -> None:
        super().__init__(name="VelocityRule", weight=weight)

    async def evaluate(
        self,
        transaction: Transaction,
        user_rules: UserRulesView,
        db: AsyncSession,
    ) -> RuleResult:
        limit = user_rules.max_transactions_per_hour
        if limit is None:
            return RuleResult(triggered=False, message="No velocity limit set", risk_contribution=0)
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.user_id == transaction.user_id,
                Transaction.created_at >= since,
            )
        )
        count = result.scalar() or 0
        if count <= limit:
            return RuleResult(
                triggered=False,
                message=f"Transactions in last hour {count} within limit {limit}",
                risk_contribution=0,
            )
        return RuleResult(
            triggered=True,
            message=f"Transactions in last hour {count} exceed limit {limit}",
            risk_contribution=self.weight,
        )


class MonthlyLimitRule(BaseRule):
    """Triggers when sum of user transactions this month + current amount > monthly_spending_limit."""

    def __init__(self, weight: int = 35) -> None:
        super().__init__(name="MonthlyLimitRule", weight=weight)

    async def evaluate(
        self,
        transaction: Transaction,
        user_rules: UserRulesView,
        db: AsyncSession,
    ) -> RuleResult:
        limit = user_rules.monthly_spending_limit
        if limit is None:
            return RuleResult(triggered=False, message="No monthly limit set", risk_contribution=0)
        # Sum same month same year, including current transaction for "would exceed" check
        start_of_month = transaction.created_at.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        result = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == transaction.user_id,
                Transaction.created_at >= start_of_month,
            )
        )
        total = float(result.scalar() or 0)
        if total <= limit:
            return RuleResult(
                triggered=False,
                message=f"Monthly total {total} within limit {limit}",
                risk_contribution=0,
            )
        return RuleResult(
            triggered=True,
            message=f"Monthly total {total} exceeds limit {limit}",
            risk_contribution=self.weight,
        )


class CountryBlockRule(BaseRule):
    """Triggers when transaction.country is in user_rules.blocked_countries."""

    def __init__(self, weight: int = 40) -> None:
        super().__init__(name="CountryBlockRule", weight=weight)

    async def evaluate(
        self,
        transaction: Transaction,
        user_rules: UserRulesView,
        db: AsyncSession,
    ) -> RuleResult:
        blocked = user_rules.blocked_countries or []
        if not blocked:
            return RuleResult(triggered=False, message="No countries blocked", risk_contribution=0)
        country = (transaction.country or "").strip().upper()
        if not country:
            return RuleResult(triggered=False, message="Transaction has no country", risk_contribution=0)
        normalized_blocked = [c.strip().upper() for c in blocked if c]
        if country not in normalized_blocked:
            return RuleResult(
                triggered=False,
                message=f"Country {country} not in blocked list",
                risk_contribution=0,
            )
        return RuleResult(
            triggered=True,
            message=f"Country {country} is blocked",
            risk_contribution=self.weight,
        )


async def _get_user_rules(user_id: int, db: AsyncSession) -> UserRulesView:
    """Load UserRuleConfig for user or return defaults."""
    result = await db.execute(
        select(UserRuleConfig).where(UserRuleConfig.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return _default_user_rules()
    return UserRulesView(
        max_transaction_amount=row.max_transaction_amount,
        max_transactions_per_hour=row.max_transactions_per_hour,
        monthly_spending_limit=row.monthly_spending_limit,
        blocked_countries=row.blocked_countries or [],
    )


class RuleEngine:
    """
    Registers rule strategies and evaluates a transaction by ID.
    Risk score = sum of triggered rules' weights; decision ALLOW / REVIEW / BLOCK.
    """

    ALLOW_THRESHOLD = 40
    REVIEW_MAX = 70

    def __init__(self) -> None:
        self._rules: list[BaseRule] = []

    def register_rule(self, rule: BaseRule) -> None:
        """Register a rule strategy for evaluation."""
        self._rules.append(rule)

    async def evaluate_transaction(
        self,
        transaction_id: int,
        db: AsyncSession,
    ) -> EvaluationResult:
        """
        Load transaction and user config, run all registered rules,
        then compute risk_score and decision.
        """
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        transaction = result.scalar_one_or_none()
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        user_rules = await _get_user_rules(transaction.user_id, db)
        rule_results: list[RuleResult] = []
        for rule in self._rules:
            rr = await rule.evaluate(transaction, user_rules, db)
            rr.rule_name = rule.name
            rule_results.append(rr)

        risk_score = sum(r.risk_contribution for r in rule_results)
        risk_score = min(100, risk_score)
        decision = _decision_from_score(risk_score)
        return EvaluationResult(
            transaction_id=transaction_id,
            risk_score=risk_score,
            decision=decision,
            rule_results=rule_results,
        )


def create_default_engine() -> RuleEngine:
    """Factory: RuleEngine with all concrete rules registered."""
    engine = RuleEngine()
    engine.register_rule(MaxAmountRule(weight=30))
    engine.register_rule(VelocityRule(weight=25))
    engine.register_rule(MonthlyLimitRule(weight=35))
    engine.register_rule(CountryBlockRule(weight=40))
    return engine
