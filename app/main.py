from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import get_tenant_id
from app.db.database import engine
from app.db.seed import run_seed

# Database is managed via Alembic migrations.
# After modifying models, run:
#   alembic revision --autogenerate -m "description"
#   alembic upgrade head

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_seed(engine)
    yield

app = FastAPI(title="PersonalFinances API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # API Gateway handles real CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.transactions import router as transactions_router
from app.api.batch import router as batch_router
from app.api.debts import router as debts_router
from app.api.fixed_incomes import router as fixed_incomes_router
from app.api.accounts import router as accounts_router
from app.api.categories import router as categories_router

app.include_router(transactions_router)
app.include_router(batch_router)
app.include_router(debts_router)
app.include_router(fixed_incomes_router)
app.include_router(accounts_router)
app.include_router(categories_router)

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "PersonalFinances Microservice is running."}


@app.get("/api/secure-ping")
def secure_ping(tenant_id: str = Depends(get_tenant_id)):
    return {"status": "ok", "tenant_id": tenant_id, "message": "Secure connection established."}
