import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from app.core.config import settings

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}

async def save_upload_file(upload_file: UploadFile, tenant_id: str) -> str:
    """
    Guarda un archivo de manera asíncrona validando su tamaño y tipo mime.
    Retorna la ruta relativa donde fue guardado.
    """
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Tipo de archivo no soportado: {upload_file.content_type}. Solo se permiten imágenes (JPEG/PNG) y PDFs."
        )

    # El tamaño en bytes puede ser inferido leyendo en chunks o si hay un header (no siempre confiable)
    # Por ahora, leemos el archivo completo a memoria para validar, o podemos usar el spool de starlette
    # Para 10MB es seguro leer a memoria.
    
    content = await upload_file.read()
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo excede el tamaño máximo permitido de {settings.MAX_FILE_SIZE_MB}MB."
        )

    # Determinar extensión
    ext = ".jpg"
    if upload_file.content_type == "image/png":
        ext = ".png"
    elif upload_file.content_type == "application/pdf":
        ext = ".pdf"
    
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    
    # Asegurar directorio
    tenant_dir = os.path.join(settings.UPLOAD_DIR, tenant_id)
    os.makedirs(tenant_dir, exist_ok=True)
    
    file_path = os.path.join(tenant_dir, filename)
    
    # Escribir a disco
    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(content)
        
    return file_path
