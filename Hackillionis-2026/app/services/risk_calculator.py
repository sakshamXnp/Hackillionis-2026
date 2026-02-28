"""Risk score calculation service for transactions."""

from app.schemas.evaluation import EvaluationRequest, RuleMatchResult


class RiskCalculator:
    """
    Computes a normalized risk score (0.0 - 1.0) for a transaction.

    Factors: amount thresholds, number of matched (restrictive) rules,
    and optional metadata signals.
    """

    # Amount thresholds (USD) that increase risk
    HIGH_AMOUNT_THRESHOLD = 10_000.0
    MEDIUM_AMOUNT_THRESHOLD = 1_000.0

    @classmethod
    def calculate(
        cls,
        request: EvaluationRequest,
        matched_results: list[RuleMatchResult],
    ) -> float:
        """
        Compute risk score from 0.0 (low) to 1.0 (high).

        - Base from amount tier
        - Increase for each matching rule (rule suggests scrutiny)
        - Cap at 1.0
        """
        score = 0.0

        # Amount-based component (0 - 0.5)
        if request.amount >= cls.HIGH_AMOUNT_THRESHOLD:
            score += 0.5
        elif request.amount >= cls.MEDIUM_AMOUNT_THRESHOLD:
            score += 0.25

        # Matched rules component (0 - 0.5)
        matched_count = sum(1 for r in matched_results if r.matched)
        score += min(0.5, matched_count * 0.15)

        return min(1.0, round(score, 4))
