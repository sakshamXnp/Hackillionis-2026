"""Rule evaluation endpoint (Strategy-based engine by transaction_id)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.evaluation import (
    EvaluationByTransactionRequest,
    EvaluationResponse,
    RuleResultSchema,
)
from app.services.rule_engine import (
    create_default_engine,
    EvaluationResult,
)

router = APIRouter()

# Single engine instance with all concrete rules registered
_engine = create_default_engine()


def _to_response(result: EvaluationResult) -> EvaluationResponse:
    """Map EvaluationResult to Pydantic response schema."""
    return EvaluationResponse(
        transaction_id=result.transaction_id,
        risk_score=result.risk_score,
        decision=result.decision,
        rule_results=[
            RuleResultSchema(
                rule_name=rr.rule_name,
                triggered=rr.triggered,
                message=rr.message,
                risk_contribution=rr.risk_contribution,
            )
            for rr in result.rule_results
        ],
    )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_transaction(
    payload: EvaluationByTransactionRequest,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Evaluate all registered payment rules for an existing transaction by ID.

    Uses per-user RuleConfig from the database. Returns risk_score (0-100),
    decision (ALLOW / REVIEW / BLOCK), and per-rule results.
    """
    try:
        result = await _engine.evaluate_transaction(payload.transaction_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _to_response(result)
