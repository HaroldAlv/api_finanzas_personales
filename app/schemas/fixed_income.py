from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Requests ---

class FixedIncomeCreate(BaseModel):
    """Crear configuración de ingreso fijo."""
    name: str
    amount: float
    frequency: str = "monthly"              # weekly, biweekly, monthly, yearly
    payment_day: Optional[int] = None       # Day of month (1-31)
    id_destination_account: int


class FixedIncomeUpdate(BaseModel):
    """Actualizar ingreso fijo."""
    name: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    payment_day: Optional[int] = None
    id_destination_account: Optional[int] = None


class ConfirmPaymentRequest(BaseModel):
    """Confirmar pago de un ingreso fijo."""
    amount: float
    date: Optional[datetime] = None
    id_from_account: Optional[int] = None


# --- Responses ---

class FixedIncomeResponse(BaseModel):
    """DTO de respuesta para ingresos fijos."""
    id: int
    name: str
    amount: float
    frequency: str
    payment_day: Optional[int] = None
    id_destination_account: int
    is_active: bool

    class Config:
        from_attributes = True


class FixedIncomePaymentResponse(BaseModel):
    """DTO de respuesta para registros de pago."""
    id: int
    id_fixed_income: int
    amount: float
    date: datetime
    confirmed: bool
    id_transaction: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True
