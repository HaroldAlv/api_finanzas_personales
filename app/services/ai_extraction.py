import base64
import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlmodel import Session, select
from app.models.financial import Category
from app.core.config import settings
import asyncio
import mimetypes
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class GeminiExtractionSchema(BaseModel):
    amount: float = Field(description="Monto total de la transacción")
    date: str = Field(description="Fecha en formato YYYY-MM-DD")
    merchant: str = Field(description="Nombre del comercio")
    description: Optional[str] = Field(default=None, description="Descripción breve del ítem/servicio")
    suggested_category: Optional[str] = Field(default=None, description="Categoría sugerida")
    confidence: float = Field(description="Confianza de la extracción entre 0 y 1")


logger = logging.getLogger(__name__)


# Cliente httpx compartido (inicializar al arrancar la app)
_httpx_client: httpx.AsyncClient | None = None


def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient()
    return _httpx_client


# Setup OpenAI if API key is provided
try:
    from openai import AsyncOpenAI
    from google import genai as google_genai
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        gemini_client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
except ImportError:
    openai_client = None
    gemini_client = None


@dataclass
class ExtractionResult:
    amount: float
    date: str
    merchant: str
    description: Optional[str]
    suggested_category_id: Optional[int]
    confidence: float
    raw_response: dict

GENERIC_CATEGORIES = [
    "Alimentación",
    "Transporte",
    "Vivienda",
    "Servicios",
    "Ocio y Entretenimiento",
    "Salud",
    "Educación",
    "Ropa y Calzado",
    "Otros"
]

def ensure_generic_categories(session: Session, tenant_id: str) -> List[Category]:
    statement = select(Category).where(Category.tenant_id == tenant_id, Category.is_active == True)
    categories = session.exec(statement).all()
    
    if not categories:
        for cat_name in GENERIC_CATEGORIES:
            new_cat = Category(name=cat_name, tenant_id=tenant_id, is_active=True, description="Categoría genérica generada automáticamente.")
            session.add(new_cat)
        session.commit()
        categories = session.exec(statement).all()
        
    return list(categories)

def encode_image(file_path: str) -> str:
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def build_prompt(categories: List[Category]) -> str:
    cat_list = ", ".join([f"'{c.name}'" for c in categories])
    return f"""Analiza esta imagen/documento financiero y extrae los siguientes datos en formato JSON:
{{
  "amount": <float>,
  "date": "<YYYY-MM-DD>",
  "merchant": "<nombre del comercio>",
  "description": "<descripción/concepto extraído>",
  "suggested_category": "<DEBE SER EXACTAMENTE UNA DE ESTAS: [{cat_list}]>",
  "confidence": <float 0-1>
}}
Si no puedes extraer un campo con certeza, usa null. Devuelve SOLO el JSON sin markdown ni backticks, para que pueda ser parseado directamente."""

async def extract_transaction_data(
    file_path: str,
    session: Session,
    tenant_id: str,
    ) -> ExtractionResult:
    categories = ensure_generic_categories(session, tenant_id)
    prompt = build_prompt(categories)
    
    # I/O no bloqueante
    base64_image, mime_type = await asyncio.to_thread(_encode_image_with_mime, file_path)
    
    raw_json_str = await _call_ai_provider(prompt, base64_image, mime_type)
    
    try:
        parsed_data = json.loads(raw_json_str)
    except json.JSONDecodeError:
        logger.error(
            "No se pudo parsear la respuesta del AI provider. "
            "Raw response: %.200s", raw_json_str
        )
        parsed_data = {}
    
    return _build_extraction_result(parsed_data, categories)

def _encode_image_with_mime(file_path: str) -> tuple[str, str]:
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "image/jpeg"
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return encoded, mime_type

async def _call_ai_provider(
    prompt: str,
    base64_image: str,
    mime_type: str,
    ) -> str:
    if settings.AI_PROVIDER == "openai" and openai_client:
        return await _call_openai(prompt, base64_image, mime_type)
    elif settings.AI_PROVIDER == "ollama":
        return await _call_ollama(prompt, base64_image)
    elif settings.AI_PROVIDER == "gemini" and gemini_client:
        return await _call_gemini(prompt, base64_image, mime_type)
    else:
        logger.warning("AI provider no configurado, usando respuesta dummy.")
        return (
            '{"amount": 150.0, "date": "2026-06-24", "merchant": "Dummy Store",'
            ' "description": "Dummy item", "suggested_category": "Otros", "confidence": 0.5}'
        )

async def _call_openai(prompt: str, base64_image: str, mime_type: str) -> str:
    try:
        response = await openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }],
        response_format={"type": "json_object"},
        max_tokens=1024, # margen suficiente para JSON completo
        )
        return response.choices[0].message.content or "{}"
    except Exception as exc:
        logger.exception("Error llamando a OpenAI: %s", exc)
        raise

async def _call_ollama(prompt: str, base64_image: str) -> str:
    client = get_httpx_client()
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "images": [base64_image],
        "stream": False,
        "format": "json",
    }
    try:
        res = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=60.0,
            )
        res.raise_for_status()
        return res.json().get("response", "{}")
    except httpx.HTTPStatusError as exc:
        logger.exception("Ollama respondió con error HTTP %s: %s", exc.response.status_code, exc)
        raise
    except httpx.RequestError as exc:
        logger.exception("Error de red al llamar a Ollama: %s", exc)
        raise

def _build_extraction_result(
        parsed_data: dict,
        categories: list,
    ) -> ExtractionResult:
    # Resolver categoría
    suggested_cat_name = parsed_data.get("suggested_category")
    cat_id = None
    if suggested_cat_name:
        cat_id = next(
            (c.id for c in categories if c.name.lower() == suggested_cat_name.lower()),
            None,
        )

    # Validar fecha
    raw_date = parsed_data.get("date") or ""
    try:
        datetime.strptime(raw_date, "%Y-%m-%d")
        date = raw_date
    except ValueError:
        logger.warning("Fecha inválida recibida del AI: %r, usando fallback.", raw_date)
        date = "2026-01-01"

    return ExtractionResult(
        amount=float(parsed_data.get("amount") or 0.0),
        date=date,
        merchant=parsed_data.get("merchant") or "Desconocido",
        description=parsed_data.get("description"),
        suggested_category_id=cat_id,
        confidence=float(parsed_data.get("confidence") or 0.0),
        raw_response=parsed_data,
    )

async def _call_gemini(prompt: str, base64_image: str, mime_type: str) -> str:
    try:
        image_bytes = base64.b64decode(base64_image)
        # El SDK de google-genai no es nativamente async en todas sus versiones,
        # así que lo corremos en un thread para no bloquear el event loop.
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=[
                prompt,
                google_genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=google_genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema= GeminiExtractionSchema,
                max_output_tokens=1024,
            ),
        )
        return response.text or "{}"
    except Exception as exc:
        logger.exception("Error llamando a Gemini: %s", exc)
        raise


# async def extract_transaction_data(file_path: str, session: Session, tenant_id: str) -> ExtractionResult:
#     categories = ensure_generic_categories(session, tenant_id)
#     prompt = build_prompt(categories)
    
#     # We'll support OpenAI for images first, PDF support would require PDF-to-image or text extraction
#     # Assuming the file is an image for now in this MVP
#     base64_image = encode_image(file_path)
    
#     raw_json_str = ""
#     if settings.AI_PROVIDER == "openai" and openai_client:
#         response = await openai_client.chat.completions.create(
#             model=settings.OPENAI_MODEL,
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {"type": "text", "text": prompt},
#                         {
#                             "type": "image_url",
#                             "image_url": {
#                                 "url": f"data:image/jpeg;base64,{base64_image}",
#                                 "detail": "high"
#                             }
#                         }
#                     ]
#                 }
#             ],
#             response_format={"type": "json_object"},
#             max_tokens=500
#         )
#         raw_json_str = response.choices[0].message.content
#     elif settings.AI_PROVIDER == "ollama":
#         async with httpx.AsyncClient() as client:
#             payload = {
#                 "model": settings.OLLAMA_MODEL,
#                 "prompt": prompt,
#                 "images": [base64_image],
#                 "stream": False,
#                 "format": "json"
#             }
#             res = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60.0)
#             res.raise_for_status()
#             data = res.json()
#             raw_json_str = data.get("response", "{}")
#     else:
#         # Fallback dummy for testing if neither is configured
#         raw_json_str = '{"amount": 150.0, "date": "2026-06-24", "merchant": "Dummy Store", "description": "Dummy item", "suggested_category": "Otros", "confidence": 0.5}'
        
#     try:
#         parsed_data = json.loads(raw_json_str)
#     except json.JSONDecodeError:
#         parsed_data = {}
        
#     suggested_cat_name = parsed_data.get("suggested_category")
#     cat_id = None
#     if suggested_cat_name:
#         for c in categories:
#             if c.name.lower() == suggested_cat_name.lower():
#                 cat_id = c.id
#                 break
                
#     # Fallback si falla
#     amount = float(parsed_data.get("amount") or 0.0)
#     date = parsed_data.get("date") or "2026-01-01"
    
#     return ExtractionResult(
#         amount=amount,
#         date=date,
#         merchant=parsed_data.get("merchant") or "Desconocido",
#         description=parsed_data.get("description"),
#         suggested_category_id=cat_id,
#         confidence=float(parsed_data.get("confidence") or 0.0),
#         raw_response=parsed_data
#     )
