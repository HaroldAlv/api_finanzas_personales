import os
import asyncio
from typing import List
from datetime import datetime
from sqlmodel import Session
from app.db.database import engine
from app.models.financial import BatchIngestion, Transaction, Account
from app.services.ai_extraction import extract_transaction_data

async def process_batch(batch_id: int, file_paths: List[str], tenant_id: str, account_id: int):
    """
    Procesamiento asíncrono en segundo plano para lotes de archivos.
    """
    # En BackgroundTasks estamos en otro contexto, necesitamos nuestra propia sesión
    with Session(engine) as session:
        batch = session.get(BatchIngestion, batch_id)
        if not batch:
            return
            
        total_processed = 0
        total_failed = 0
        
        for file_path in file_paths:
            try:
                # Extraer datos
                extraction = await extract_transaction_data(file_path, session, tenant_id)
                
                # Parsear fecha
                try:
                    tx_date = datetime.strptime(extraction.date, "%Y-%m-%d")
                except ValueError:
                    tx_date = datetime.utcnow()
                    
                # Crear transacción
                new_tx = Transaction(
                    amount=extraction.amount,
                    date=tx_date,
                    merchant=extraction.merchant,
                    description=extraction.description,
                    source="bulk",
                    original_file_path=file_path,
                    status="PendingReview",
                    batch_id=batch_id,
                    account_id=account_id,
                    category_id=extraction.suggested_category_id,
                    tenant_id=tenant_id
                )
                session.add(new_tx)
                total_processed += 1
            except Exception as e:
                # Log error
                print(f"Error procesando {file_path}: {str(e)}")
                total_failed += 1
                
        # Actualizar estado del lote
        batch.total_processed = total_processed
        batch.total_failed = total_failed
        batch.status = "Completed" if total_failed == 0 else "PartiallyCompleted"
        if total_failed == len(file_paths) and len(file_paths) > 0:
            batch.status = "Failed"
        batch.completed_at = datetime.utcnow()
        
        session.add(batch)
        session.commit()
