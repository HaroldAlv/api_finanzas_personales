from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import Transaction, Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse, SmartIngestionResponse
from app.services.file_handler import save_upload_file
from app.services.ai_extraction import extract_transaction_data

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("", response_model=TransactionResponse)
def create_transaction(
    tx_in: TransactionCreate, 
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Registro manual de transacción (Módulo A)."""
    new_tx = Transaction(
        amount=tx_in.amount,
        date=tx_in.date,
        merchant=tx_in.merchant,
        description=tx_in.description,
        account_id=tx_in.account_id,
        category_id=tx_in.category_id,
        tenant_id=tenant_id,
        status="Confirmed",
        source="manual"
    )
    session.add(new_tx)
    session.commit()
    session.refresh(new_tx)
    return new_tx

@router.post("/smart-ingest", response_model=SmartIngestionResponse)
async def smart_ingest(
    account_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Smart Ingestion de un solo archivo con IA (Módulo A)."""
    # 1. Guardar archivo
    file_path = await save_upload_file(file, tenant_id)
    
    # 2. Extraer datos con IA
    try:
        extraction = await extract_transaction_data(file_path, session, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en IA: {str(e)}")
        
    # Parsear fecha
    try:
        tx_date = datetime.strptime(extraction.date, "%Y-%m-%d")
    except ValueError:
        tx_date = datetime.utcnow()

    # 3. Guardar en BD como PendingReview
    new_tx = Transaction(
        amount=extraction.amount,
        date=tx_date,
        merchant=extraction.merchant,
        description=extraction.description,
        source="smart_ingestion",
        original_file_path=file_path,
        status="PendingReview",
        account_id=account_id,
        category_id=extraction.suggested_category_id,
        tenant_id=tenant_id
    )
    session.add(new_tx)
    session.commit()
    session.refresh(new_tx)
    
    return SmartIngestionResponse(
        transaction=new_tx,
        ai_confidence=extraction.confidence,
        raw_extraction=extraction.raw_response,
        message="Archivo procesado correctamente."
    )

@router.get("", response_model=List[TransactionResponse])
def get_transactions(
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
    status: Optional[str] = None
):
    """Obtener transacciones del tenant."""
    statement = select(Transaction).where(
        Transaction.tenant_id == tenant_id,
        Transaction.is_active == True
    )
    if status:
        statement = statement.where(Transaction.status == status)
        
    transactions = session.exec(statement).all()
    return transactions

@router.patch("/{tx_id}/confirm", response_model=TransactionResponse)
def confirm_transaction(
    tx_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Confirmar una transacción PendingReview."""
    tx = session.get(Transaction, tx_id)
    if not tx or tx.tenant_id != tenant_id or not tx.is_active:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
        
    tx.status = "Confirmed"
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx

@router.delete("/{tx_id}")
def delete_transaction(
    tx_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Soft Delete."""
    tx = session.get(Transaction, tx_id)
    if not tx or tx.tenant_id != tenant_id or not tx.is_active:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
        
    tx.is_active = False
    session.add(tx)
    session.commit()
    return {"message": "Transacción eliminada"}
