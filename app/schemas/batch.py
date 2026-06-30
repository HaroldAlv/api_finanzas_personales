from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.transaction import TransactionResponse

class BatchCreateResponse(BaseModel):
    """Respuesta inmediata al crear un lote."""
    batch_id: int
    file_count: int
    status: str
    message: str

class BatchStatusResponse(BaseModel):
    """Estado actual de un lote en procesamiento."""
    batch_id: int
    status: str
    file_count: int
    total_processed: int
    total_failed: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    transactions: List[TransactionResponse] = []

    class Config:
        from_attributes = True
