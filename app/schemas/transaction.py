from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Requests ---
class TransactionCreate(BaseModel):
    """Registro manual de transacción."""
    amount: float
    date: datetime
    merchant: str
    description: Optional[str] = None
    account_id: int
    category_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    """Actualización de transacción."""
    amount: Optional[float] = None
    date: Optional[datetime] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None
    category_id: Optional[int] = None

# --- Responses ---
class TransactionResponse(BaseModel):
    """DTO de respuesta."""
    id: int
    amount: float
    date: datetime
    merchant: str
    description: Optional[str] = None
    status: str
    source: str
    account_id: int
    category_id: Optional[int] = None
    batch_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

class SmartIngestionResponse(BaseModel):
    """Resultado de la extracción IA de un solo archivo."""
    transaction: TransactionResponse
    ai_confidence: float
    raw_extraction: dict
    message: str
