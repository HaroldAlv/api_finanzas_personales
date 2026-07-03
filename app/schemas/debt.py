from pydantic import BaseModel
from typing import Optional


# --- Requests ---

class DebtCreate(BaseModel):
    """Crear una deuda u obligación."""
    name: str
    description: Optional[str] = None
    total_amount: Optional[float] = None
    minimum_payment: Optional[float] = None
    cutoff_day: int
    due_day: int
    interest_rate: Optional[float] = None


class DebtUpdate(BaseModel):
    """Actualizar una deuda."""
    name: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[float] = None
    minimum_payment: Optional[float] = None
    cutoff_day: Optional[int] = None
    due_day: Optional[int] = None
    interest_rate: Optional[float] = None


# --- Responses ---

class DebtResponse(BaseModel):
    """DTO de respuesta para deudas."""
    id: int
    name: str
    description: Optional[str] = None
    total_amount: Optional[float] = None
    minimum_payment: Optional[float] = None
    cutoff_day: int
    due_day: int
    interest_rate: Optional[float] = None
    is_active: bool

    class Config:
        from_attributes = True
