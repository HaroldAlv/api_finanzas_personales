import base64
import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlmodel import Session, select
from app.models.financial import Account, Category
from app.core.config import settings
import asyncio
import mimetypes
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from markitdown import MarkItDown

class GeminiExtractionSchema(BaseModel):
    amount: float = Field(description="Monto total de la transacción")
    date: str = Field(description="Fecha en formato YYYY-MM-DD")
    name_destination: str = Field(description="Nombre del comercio o destinatario del pago")
    name_from: Optional[str] = Field(default=None, description="Nombre del emisor del pago, si es inferible del recibo")
    description: Optional[str] = Field(default=None, description="Descripción breve del ítem/servicio")
    suggested_category: Optional[str] = Field(default=None, description="Categoría sugerida")
    from_account: Optional[str] = Field(default=None, description="Nombre de la cuenta origen, si es inferible del recibo")
    destination_account: Optional[str] = Field(default=None, description="Nombre de la cuenta destino, si es inferible del recibo")
    confidence: float = Field(description="Confianza de la extracción entre 0 y 1")


logger = logging.getLogger(__name__)


# Cliente httpx compartido (inicializar al arrancar la app)
_httpx_client: httpx.AsyncClient | None = None


def get_httpx_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient()
    return _httpx_client


# Setup AI clients (will stay None if no API key configured)
openai_client = None
gemini_client = None

try:
    from openai import AsyncOpenAI
    from google import genai as google_genai
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        gemini_client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    if settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
except ImportError:
    logger.warning("openai o google-genai no instalados, la IA no estará disponible")


@dataclass
class ExtractionResult:
    amount: float
    date: str
    name_destination: str
    name_from: Optional[str]
    description: Optional[str]
    suggested_category_id: Optional[int]
    suggested_from_account_id: Optional[int]
    suggested_destination_account_id: Optional[int]
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

def ensure_generic_categories(session: Session) -> List[Category]:
    """Load or create generic categories. Category is now a global table (no tenant_id)."""
    statement = select(Category)
    categories = session.exec(statement).all()

    if not categories:
        for cat_name in GENERIC_CATEGORIES:
            new_cat = Category(name=cat_name, description="Categoría genérica generada automáticamente.")
            session.add(new_cat)
        session.commit()
        categories = session.exec(statement).all()

    return list(categories)

def encode_image(file_path: str) -> str:
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def build_prompt(categories: List[Category], accounts: List[Account]) -> str:
    cat_list = ", ".join([f"'{c.name}'" for c in categories])
    acc_list = ", ".join([f"'{a.name}' ({a.type})" for a in accounts])
    masked = settings.USER_ACCOUNT_NUMBER[-4:]
    return f"""Información del usuario: {settings.USER_FULL_NAME}, su cuenta principal es Banco Caja Social número {settings.USER_ACCOUNT_NUMBER} (aparece como *******{masked} en capturas). Si ves este número en la imagen, la cuenta origen o destino es 'Banco Caja Social'.

Analiza esta imagen/documento financiero y extrae los siguientes datos en formato JSON:
{{
  "amount": <float>,
  "date": "<YYYY-MM-DD>",
  "name_destination": "<nombre del comercio o destinatario del pago>",
  "name_from": "<nombre del emisor del pago, si es inferible del recibo, de lo contrario null>",
  "from_account": "<DEBE SER EXACTAMENTE UNA DE ESTAS CUENTAS: [{acc_list}], o null si no es inferible>",
  "destination_account": "<DEBE SER EXACTAMENTE UNA DE ESTAS CUENTAS: [{acc_list}], o null si no es inferible>",
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
    categories = ensure_generic_categories(session)
    accounts = session.exec(select(Account)).all()
    prompt = build_prompt(categories, accounts)

    # Paso 1: Intentar MarkItDown (solo texto, ahorra tokens)
    raw_json_str = None
    if settings.USE_MARKITDOWN:
        markdown_text = await asyncio.to_thread(preprocess_with_markitdown, file_path)
        if markdown_text:
            raw_json_str = await _call_ai_provider_text_only(prompt, markdown_text)

    # Paso 2: Fallback a visión LLM si MarkItDown no dio resultado
    if raw_json_str is None:
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

    return _build_extraction_result(parsed_data, categories, accounts)

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
            '{"amount": 150.0, "date": "2026-06-24", "name_destination": "Dummy Store",'
            ' "name_from": null, "description": "Dummy item", "suggested_category": "Otros", "confidence": 0.5}'
        )

async def _call_ai_provider_text_only(prompt: str, markdown_text: str) -> str:
    """Envía solo texto al AI provider sin imagen. Máximo ahorro de tokens."""
    full_prompt = f"{prompt}\n\nContenido extraído del documento:\n{markdown_text}"

    if settings.AI_PROVIDER == "openai" and openai_client:
        try:
            response = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
            return response.choices[0].message.content or "{}"
        except Exception as exc:
            logger.exception("Error llamando a OpenAI (texto): %s", exc)
            raise

    elif settings.AI_PROVIDER == "ollama":
        client = get_httpx_client()
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": full_prompt,
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

    elif settings.AI_PROVIDER == "gemini" and gemini_client:
        try:
            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=google_genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiExtractionSchema,
                    max_output_tokens=1024,
                ),
            )
            return response.text or "{}"
        except Exception as exc:
            logger.exception("Error llamando a Gemini (texto): %s", exc)
            raise

    else:
        logger.warning("AI provider no configurado, usando respuesta dummy.")
        return (
            '{"amount": 150.0, "date": "2026-06-24", "name_destination": "Dummy Store",'
            ' "name_from": null, "description": "Dummy item", "suggested_category": "Otros", "confidence": 0.5}'
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
        accounts: list,
    ) -> ExtractionResult:
    # Resolver categoría
    suggested_cat_name = parsed_data.get("suggested_category")
    cat_id = None
    if suggested_cat_name:
        cat_id = next(
            (c.id for c in categories if c.name.lower() == suggested_cat_name.lower()),
            None,
        )

    # Resolver cuentas
    from_account_id = None
    from_account_name = parsed_data.get("from_account")
    if from_account_name:
        from_account_id = next(
            (a.id for a in accounts if a.name.lower() == from_account_name.lower()),
            None,
        )

    destination_account_id = None
    destination_account_name = parsed_data.get("destination_account")
    if destination_account_name:
        destination_account_id = next(
            (a.id for a in accounts if a.name.lower() == destination_account_name.lower()),
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
        name_destination=parsed_data.get("name_destination") or "Desconocido",
        name_from=parsed_data.get("name_from"),
        description=parsed_data.get("description"),
        suggested_category_id=cat_id,
        suggested_from_account_id=from_account_id,
        suggested_destination_account_id=destination_account_id,
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


def preprocess_with_markitdown(file_path:str) -> str | None:
    """
    Convierte un archivo (PDF/imagen) a Markdown usando MarkItDown.
    Retorna el texto en Markdown, o None si no se pudo extraer contenido útil.
    """
    md = MarkItDown()
    result = md.convert(file_path)
    text = result.text_content.strip()
    if len(text) < settings.MARKITDOWN_MIN_CHARS:
        return None
    return text