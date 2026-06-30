from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlmodel import Session, select
from typing import List

from app.db.database import get_session
from app.core.security import get_tenant_id
from app.models.financial import BatchIngestion, Transaction
from app.schemas.batch import BatchCreateResponse, BatchStatusResponse
from app.services.file_handler import save_upload_file
from app.services.batch_processor import process_batch

router = APIRouter(prefix="/batch", tags=["Batch Processing"])

@router.post("/ingest", response_model=BatchCreateResponse)
async def bulk_ingest(
    background_tasks: BackgroundTasks,
    account_id: int = Form(...),
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Carga masiva de archivos (hasta 10). Módulo B."""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Máximo 10 archivos permitidos por lote.")
        
    # Guardar archivos
    saved_paths = []
    for f in files:
        path = await save_upload_file(f, tenant_id)
        saved_paths.append(path)
        
    # Crear lote en BD
    batch = BatchIngestion(
        tenant_id=tenant_id,
        status="Processing",
        file_count=len(files)
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)
    
    # Enviar a background task
    background_tasks.add_task(
        process_batch, 
        batch_id=batch.id, 
        file_paths=saved_paths, 
        tenant_id=tenant_id,
        account_id=account_id
    )
    
    return BatchCreateResponse(
        batch_id=batch.id,
        file_count=batch.file_count,
        status=batch.status,
        message="Lote en procesamiento."
    )

@router.get("/{batch_id}", response_model=BatchStatusResponse)
def get_batch_status(
    batch_id: int,
    session: Session = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id)
):
    """Consultar estado del lote y sus transacciones."""
    batch = session.get(BatchIngestion, batch_id)
    if not batch or batch.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
        
    return batch
