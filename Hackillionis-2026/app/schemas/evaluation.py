"""Evaluation request/response schemas for Strategy-based rule engine."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationByTransactionRequest(BaseModel):
    """Request to evaluate rules for an existing transaction by ID."""

    transaction_id: int = Field(..., gt=0, description="ID of the transaction to evaluate")


class RuleResultSchema(BaseModel):
    """Single rule evaluation result for API response."""

    rule_name: str = Field(..., description="Name of the rule that was evaluated")
    triggered: bool = Field(..., description="Whether the rule was triggered (violation)")
    message: str = Field(..., description="Human-readable result message")
    risk_contribution: int = Field(
        ...,
        ge=0,
        le=100,
        description="Risk contribution (rule weight) when triggered",
    )


class EvaluationResponse(BaseModel):
    """Result of rule engine evaluation for a transaction."""

    transaction_id: int = Field(..., description="Evaluated transaction ID")
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Total risk score (sum of triggered rule weights)",
    )
    decision: Literal["ALLOW", "REVIEW", "BLOCK"] = Field(
        ...,
        description="ALLOW if score < 40, REVIEW if 40-70, BLOCK if > 70",
    )
    rule_results: list[RuleResultSchema] = Field(
        default_factory=list,
        description="Per-rule evaluation results",
    )


# Legacy request/response kept for backward compatibility if needed
class EvaluationRequest(BaseModel):
    """Legacy payload for ad-hoc evaluation (optional)."""

    model_config = ConfigDict(populate_by_name=True)

    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    user_id: int | None = Field(None, description="Optional user ID for context")
    metadata_: dict | None = Field(default=None, alias="metadata")


class RuleMatchResult(BaseModel):
    """Legacy single rule match result."""

    rule_id: int
    rule_name: str
    action_type: str
    matched: bool
