from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import FixedIncome, FixedIncomePayment, Transaction
from app.schemas.fixed_income import (
    FixedIncomeCreate,
    FixedIncomeUpdate,
    FixedIncomeResponse,
    FixedIncomePaymentResponse,
    ConfirmPaymentRequest
)
from app.core.config import settings

router = APIRouter(prefix="/fixed-incomes", tags=["Fixed Incomes"])

@router.post("", response_model=FixedIncomeResponse)
def create_fixed_income(
    income_in: FixedIncomeCreate, 
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Crear configuración de ingreso fijo."""
    new_income = FixedIncome(
        name=income_in.name,
        amount=income_in.amount,
        frequency=income_in.frequency,
        payment_day=income_in.payment_day,
        id_destination_account=income_in.id_destination_account,
        tenant_id=tenant_id
    )
    session.add(new_income)
    session.commit()
    session.refresh(new_income)
    return new_income

@router.get("", response_model=List[FixedIncomeResponse])
def get_fixed_incomes(
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Listar ingresos fijos del tenant."""
    statement = select(FixedIncome).where(
        FixedIncome.tenant_id == tenant_id,
        FixedIncome.is_active == True
    )
    incomes = session.exec(statement).all()
    return incomes

@router.get("/{income_id}", response_model=FixedIncomeResponse)
def get_fixed_income(
    income_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Obtener ingreso fijo por ID."""
    income = session.get(FixedIncome, income_id)
    if not income or income.tenant_id != tenant_id or not income.is_active:
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")
    return income

@router.patch("/{income_id}", response_model=FixedIncomeResponse)
def update_fixed_income(
    income_id: int,
    income_in: FixedIncomeUpdate,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Actualizar ingreso fijo."""
    income = session.get(FixedIncome, income_id)
    if not income or income.tenant_id != tenant_id or not income.is_active:
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")

    update_data = income_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(income, key, value)

    session.add(income)
    session.commit()
    session.refresh(income)
    return income

@router.delete("/{income_id}")
def delete_fixed_income(
    income_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Soft Delete de ingreso fijo."""
    income = session.get(FixedIncome, income_id)
    if not income or income.tenant_id != tenant_id or not income.is_active:
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")
        
    income.is_active = False
    session.add(income)
    session.commit()
    return {"message": "Ingreso fijo eliminado"}

@router.post("/{income_id}/confirm-payment", response_model=FixedIncomePaymentResponse)
def confirm_fixed_income_payment(
    income_id: int,
    payment_in: ConfirmPaymentRequest,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Confirmar pago -> crear FixedIncomePayment + Transaction."""
    income = session.get(FixedIncome, income_id)
    if not income or income.tenant_id != tenant_id or not income.is_active:
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")

    tx_date = payment_in.date or datetime.utcnow()

    # 1. Crear Transacción
    new_tx = Transaction(
        amount=payment_in.amount,
        date=tx_date,
        description=f"Pago de ingreso fijo: {income.name}",
        transaction_type="income",
        name_from=settings.USER_FULL_NAME,
        name_destination=income.name,
        source="manual",
        status="Confirmed",
        id_from_account=payment_in.id_from_account,
        id_destination_account=income.id_destination_account,
        tenant_id=tenant_id
    )
    session.add(new_tx)
    session.commit()
    session.refresh(new_tx)

    # 2. Crear Pago Confirmado
    new_payment = FixedIncomePayment(
        id_fixed_income=income.id,
        amount=payment_in.amount,
        date=tx_date,
        confirmed=True,
        id_transaction=new_tx.id,
        tenant_id=tenant_id
    )
    session.add(new_payment)
    session.commit()
    session.refresh(new_payment)
    
    return new_payment
