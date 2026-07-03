from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import Account
from app.schemas.account import AccountCreate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("", response_model=List[AccountResponse])
def get_accounts(
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    accounts = session.exec(select(Account)).all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return account


@router.post("", response_model=AccountResponse)
def create_account(
    account_in: AccountCreate,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    new_account = Account(name=account_in.name, type=account_in.type)
    session.add(new_account)
    session.commit()
    session.refresh(new_account)
    return new_account
