"""API route modules."""

from fastapi import APIRouter

from app.routes import capital_one, evaluation, rules, transactions, user_rule_config, users

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(user_rule_config.router, prefix="/users", tags=["user-rules"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(transactions.router, prefix="", tags=["transactions"])
api_router.include_router(evaluation.router, prefix="", tags=["evaluation"])
api_router.include_router(capital_one.router, prefix="/capital-one", tags=["capital-one"])
