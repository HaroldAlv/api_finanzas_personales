# Sesión 3 — Implementación de Lógica de Negocio y MarkItDown (Julio 2026)

## De dónde partimos

El proyecto contaba con la refactorización V2 completa (modelos `Account`/`Category` globales, `Transaction` con origen/destino, `Debt`, `FixedIncome`, `FixedIncomePayment`). Sin embargo:

- El campo `balance` en `Account` no se usaba en ningún lado
- El campo `transaction_type` existía pero sin validación ni lógica de negocio
- La extracción IA enviaba imágenes completas al LLM (alto consumo de tokens)
- El prompt de IA no conocía las cuentas del usuario
- Las API keys estaban hardcodeadas en `config.py`
- Faltaban `GET /transactions/{id}` y `PATCH /transactions/{id}`
- No había endpoints públicos para `Account` y `Category`

## Qué se logró

### 1. Eliminación de `balance` de Account

- Se eliminó el campo `balance` del modelo `app/models/financial.py`
- Se habilitó `render_as_batch=True` en Alembic para compatibilidad con SQLite
- Se generó y aplicó migración `remove_balance_from_account`

### 2. Integración de MarkItDown (preprocesamiento IA)

- **Dependencia:** `markitdown` agregada a `requirements.txt`
- **Config:** `USE_MARKITDOWN=True`, `MARKITDOWN_MIN_CHARS=50` en `config.py`
- **Flujo nuevo en `extract_transaction_data()`:**
  1. MarkItDown convierte PDF/imagen a texto Markdown
  2. Si el texto extraído es ≥ 50 caracteres, se envía **solo texto** al LLM (ahorro ~90% tokens)
  3. Si es menor, fallback a envío de imagen completa al LLM de visión
- **Nueva función:** `preprocess_with_markitdown()` y `_call_ai_provider_text_only()`
- **Soporte:** OpenAI, Ollama y Gemini en modo solo texto

### 3. Cuentas y categorías en el prompt de IA

- `build_prompt()` ahora recibe `accounts` y genera lista de cuentas disponibles
- El prompt incluye `from_account` y `destination_account` como opciones desde la BD
- `ExtractionResult` ahora retorna `suggested_from_account_id` y `suggested_destination_account_id`
- `_build_extraction_result()` resuelve nombres de cuentas a IDs (mismo patrón que categorías)

### 4. Número de cuenta del usuario en el prompt

- `USER_ACCOUNT_NUMBER` configurado en `.env` (`24103557076`)
- El prompt informa a la IA que el número `*******7076` pertenece a Banco Caja Social
- La IA puede identificar automáticamente la cuenta origen/destino en capturas bancarias

### 5. Lógica de inserción de transacciones

| Endpoint | Cambio |
|---|---|
| `POST /transactions/smart-ingest` | Nuevo parámetro opcional `id_destination_account` (Form) + fallback a sugerencia IA |
| `POST /fixed-incomes/{id}/confirm-payment` | Nuevo campo `id_from_account` en `ConfirmPaymentRequest` |
| `POST /transactions` | Validación mediante `TransactionType` enum |
| `GET /transactions/{tx_id}` | **Nuevo** — obtener transacción por ID |
| `PATCH /transactions/{tx_id}` | **Nuevo** — actualización parcial de transacción |
| `GET /accounts` y `POST /accounts` | **Nuevos** — CRUD de cuentas |
| `GET /categories` y `POST /categories` | **Nuevos** — CRUD de categorías |

### 6. Validación con Enum

- `TransactionType` enum (`expense`, `income`, `transfer`) en `app/schemas/transaction.py`
- Validación automática vía Pydantic en `TransactionCreate`, `TransactionUpdate`, `TransactionResponse`

### 7. API Keys y .env

- Las claves se movieron de `config.py` a `.env` (ya en `.gitignore`)
- `config.py` usa defaults vacíos para `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`
- Se creó `.env.example` como plantilla para nuevos desarrolladores

### 8. Estados unificados de BatchIngestion

Los estados posibles de un lote son: `Processing`, `Completed`, `Failed`, `PartiallyCompleted`.

## Archivos modificados/creados

| Archivo | Acción |
|---|---|
| `app/core/config.py` | MODIFY — limpiar hardcodes, agregar `USER_ACCOUNT_NUMBER`, `USE_MARKITDOWN` |
| `app/services/ai_extraction.py` | MODIFY — MarkItDown, prompt con cuentas, `_call_ai_provider_text_only` |
| `app/services/batch_processor.py` | MODIFY — usar accounts sugeridos por IA |
| `app/api/transactions.py` | MODIFY — + GET/{id}, PATCH/{id}, smart-ingest con destino |
| `app/api/accounts.py` | NEW — GET list, GET by id, POST |
| `app/api/categories.py` | NEW — GET list, GET by id, POST |
| `app/schemas/transaction.py` | MODIFY — + TransactionType enum |
| `app/schemas/account.py` | NEW — AccountCreate, AccountResponse |
| `app/schemas/category.py` | NEW — CategoryCreate, CategoryResponse |
| `app/schemas/fixed_income.py` | MODIFY — + id_from_account en ConfirmPaymentRequest |
| `app/models/financial.py` | MODIFY — eliminar balance de Account |
| `app/db/migrations/versions/` | NEW — migración remove_balance_from_account |
| `app/db/migrations/env.py` | MODIFY — + render_as_batch=True |
| `.env` | NEW — variables de entorno reales |
| `.env.example` | NEW — plantilla para nuevos entornos |
| `docs/documentacion/3_implementacion_logica_negocio_markitdown.md` | NEW — este documento |

## Pendientes para futuras sesiones

- **Módulo C** — Motor de Conciliación Bancaria (subir extractos, algoritmo de matching)
- **Módulo D** — Motor de Insights (Pandas + JSON para ApexCharts)
- Posible: agregar `PATCH` y `DELETE` para `Account` y `Category`
