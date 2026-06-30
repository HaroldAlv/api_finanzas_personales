import base64
import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlmodel import Session, select
from app.models.financial import Category
from app.core.config import settings

# Setup OpenAI if API key is provided
try:
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except ImportError:
    openai_client = None

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

async def extract_transaction_data(file_path: str, session: Session, tenant_id: str) -> ExtractionResult:
    categories = ensure_generic_categories(session, tenant_id)
    prompt = build_prompt(categories)
    
    # We'll support OpenAI for images first, PDF support would require PDF-to-image or text extraction
    # Assuming the file is an image for now in this MVP
    base64_image = encode_image(file_path)
    
    raw_json_str = ""
    if settings.AI_PROVIDER == "openai" and openai_client:
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
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        raw_json_str = response.choices[0].message.content
    elif settings.AI_PROVIDER == "ollama":
        async with httpx.AsyncClient() as client:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
                "format": "json"
            }
            res = await client.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60.0)
            res.raise_for_status()
            data = res.json()
            raw_json_str = data.get("response", "{}")
    else:
        # Fallback dummy for testing if neither is configured
        raw_json_str = '{"amount": 150.0, "date": "2026-06-24", "merchant": "Dummy Store", "description": "Dummy item", "suggested_category": "Otros", "confidence": 0.5}'
        
    try:
        parsed_data = json.loads(raw_json_str)
    except json.JSONDecodeError:
        parsed_data = {}
        
    suggested_cat_name = parsed_data.get("suggested_category")
    cat_id = None
    if suggested_cat_name:
        for c in categories:
            if c.name.lower() == suggested_cat_name.lower():
                cat_id = c.id
                break
                
    # Fallback si falla
    amount = float(parsed_data.get("amount") or 0.0)
    date = parsed_data.get("date") or "2026-01-01"
    
    return ExtractionResult(
        amount=amount,
        date=date,
        merchant=parsed_data.get("merchant") or "Desconocido",
        description=parsed_data.get("description"),
        suggested_category_id=cat_id,
        confidence=float(parsed_data.get("confidence") or 0.0),
        raw_response=parsed_data
    )
