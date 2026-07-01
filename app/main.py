from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import get_tenant_id

# Database is managed via Alembic migrations.
# After modifying models, run:
#   alembic revision --autogenerate -m "description"
#   alembic upgrade head

@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.include_router(transactions_router)
app.include_router(batch_router)

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "PersonalFinances Microservice is running."}


@app.get("/api/secure-ping")
def secure_ping(tenant_id: str = Depends(get_tenant_id)):
    return {"status": "ok", "tenant_id": tenant_id, "message": "Secure connection established."}
