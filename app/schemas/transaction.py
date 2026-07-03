from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class TransactionType(str, Enum):
    expense = "expense"
    income = "income"
    transfer = "transfer"

# --- Requests ---
class TransactionCreate(BaseModel):
    """Registro manual de transacción."""
    amount: float
    date: datetime
    description: str                                    # Required
    transaction_type: TransactionType = TransactionType.expense
    name_from: str
    name_destination: str
    id_from_account: Optional[int] = None               # FK optional
    id_destination_account: Optional[int] = None        # FK optional
    category_id: Optional[int] = None

class TransactionUpdate(BaseModel):
    """Actualización de transacción."""
    amount: Optional[float] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    name_from: Optional[str] = None
    name_destination: Optional[str] = None
    id_from_account: Optional[int] = None
    id_destination_account: Optional[int] = None
    category_id: Optional[int] = None

# --- Responses ---
class TransactionResponse(BaseModel):
    """DTO de respuesta."""
    id: int
    amount: float
    date: datetime
    description: str
    transaction_type: TransactionType
    name_from: str
    name_destination: str
    status: str
    source: str
    id_from_account: Optional[int] = None
    id_destination_account: Optional[int] = None
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
