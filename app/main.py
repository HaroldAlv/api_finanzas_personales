from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from app.db.database import engine
from app.core.security import get_tenant_id

# Import models so they are registered with SQLModel metadata
from app.models import financial

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and create tables on startup
    SQLModel.metadata.create_all(engine)
    yield
    # Cleanup on shutdown (if any)

app = FastAPI(title="PersonalFinances API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # API Gateway handles real CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "PersonalFinances Microservice is running."}

@app.get("/api/secure-ping")
def secure_ping(tenant_id: str = Depends(get_tenant_id)):
    return {"status": "ok", "tenant_id": tenant_id, "message": "Secure connection established."}
