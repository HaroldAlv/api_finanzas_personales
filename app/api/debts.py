from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import Debt
from app.schemas.debt import DebtCreate, DebtUpdate, DebtResponse

router = APIRouter(prefix="/debts", tags=["Debts"])

@router.post("", response_model=DebtResponse)
def create_debt(
    debt_in: DebtCreate, 
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Crear deuda u obligación."""
    new_debt = Debt(
        name=debt_in.name,
        description=debt_in.description,
        total_amount=debt_in.total_amount,
        minimum_payment=debt_in.minimum_payment,
        cutoff_day=debt_in.cutoff_day,
        due_day=debt_in.due_day,
        interest_rate=debt_in.interest_rate,
        tenant_id=tenant_id
    )
    session.add(new_debt)
    session.commit()
    session.refresh(new_debt)
    return new_debt

@router.get("", response_model=List[DebtResponse])
def get_debts(
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Obtener deudas activas del tenant."""
    statement = select(Debt).where(
        Debt.tenant_id == tenant_id,
        Debt.is_active == True
    )
    debts = session.exec(statement).all()
    return debts

@router.get("/{debt_id}", response_model=DebtResponse)
def get_debt(
    debt_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Obtener deuda por ID."""
    debt = session.get(Debt, debt_id)
    if not debt or debt.tenant_id != tenant_id or not debt.is_active:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
    return debt

@router.patch("/{debt_id}", response_model=DebtResponse)
def update_debt(
    debt_id: int,
    debt_in: DebtUpdate,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Actualizar deuda."""
    debt = session.get(Debt, debt_id)
    if not debt or debt.tenant_id != tenant_id or not debt.is_active:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")

    update_data = debt_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(debt, key, value)

    session.add(debt)
    session.commit()
    session.refresh(debt)
    return debt

@router.delete("/{debt_id}")
def delete_debt(
    debt_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Soft Delete."""
    debt = session.get(Debt, debt_id)
    if not debt or debt.tenant_id != tenant_id or not debt.is_active:
        raise HTTPException(status_code=404, detail="Deuda no encontrada")
        
    debt.is_active = False
    session.add(debt)
    session.commit()
    return {"message": "Deuda eliminada"}
