from .transactions import router as transactions_router
from .batch import router as batch_router
from .debts import router as debts_router
from .fixed_incomes import router as fixed_incomes_router
from .accounts import router as accounts_router
from .categories import router as categories_router

__all__ = [
    "transactions_router",
    "batch_router",
    "debts_router",
    "fixed_incomes_router",
    "accounts_router",
    "categories_router",
]
