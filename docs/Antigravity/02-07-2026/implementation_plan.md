# Mejora de Modelos y Reglas de Negocio — Plan de Implementación

Implementar los cambios especificados en [2_mejora_modelos_reglas_negocio.md](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/docs/documentacion/contexto/2_mejora_modelos_reglas_negocio.md) para reestructurar el esquema de datos del microservicio PersonalFinances: convertir `Account` y `Category` en tablas globales, rediseñar `Transaction` con origen/destino, y agregar las tablas `Debt`, `FixedIncome` y `FixedIncomePayment`.

## User Review Required

> [!IMPORTANT]
> **Eliminación de la base de datos existente:** El doc especifica borrar la BD SQLite y las migraciones anteriores para empezar de cero. Todos los datos actuales en `personal_finances.db` se perderán.

> [!WARNING]
> **Claves API expuestas en `config.py`:** Los valores de `OPENAI_API_KEY` y `GEMINI_API_KEY` están hardcodeados en el archivo. Se recomienda moverlos a un `.env` después de esta implementación, pero no es parte de este scope.

---

## Proposed Changes

Se ejecutarán en el orden estricto definido por la especificación (sección 10 del doc). Cada fase depende de la anterior.

---

### Fase 1: Modelos de datos (`app/models/`)

#### [MODIFY] [financial.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/models/financial.py)

Cambios principales:
- **`Account`**: Cambiar herencia de `TenantBaseModel` → `SQLModel`. Agregar campo `type: str` (`bank`, `digital_wallet`, `cash`, `merchant`). Eliminar `balance` (no mencionado en estado deseado pero se mantiene por compatibilidad). Reemplazar relación `transactions` por `transactions_from` y `transactions_destination` con `sa_relationship_kwargs` para las dos FKs.
- **`Category`**: Cambiar herencia de `TenantBaseModel` → `SQLModel`. Se elimina implícitamente `tenant_id` e `is_active`. Mantener campos y relación intactos.
- **`Transaction`**: Eliminar `merchant` y `account_id`. Agregar `transaction_type`, `name_from`, `name_destination`, `id_from_account` (FK opcional), `id_destination_account` (FK opcional). Cambiar `description` de `Optional[str]` a `str` (requerido). Actualizar relaciones con `account_from` y `account_destination`.
- **Agregar `Debt`**: Hereda `TenantBaseModel`. Campos: `name`, `description`, `total_amount`, `minimum_payment`, `cutoff_day`, `due_day`, `interest_rate`.
- **Agregar `FixedIncome`**: Hereda `TenantBaseModel`. Campos: `name`, `amount`, `frequency`, `payment_day`, `id_destination_account` (FK a `account`).
- **Agregar `FixedIncomePayment`**: Hereda `TenantBaseModel`. Campos: `id_fixed_income` (FK), `amount`, `date`, `confirmed`, `id_transaction` (FK opcional).
- Agregar `import SQLModel` al import de `sqlmodel`.

#### [MODIFY] [__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/models/__init__.py)

- Exportar los 3 nuevos modelos: `Debt`, `FixedIncome`, `FixedIncomePayment`.

---

### Fase 2: Schemas / DTOs (`app/schemas/`)

#### [MODIFY] [transaction.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/transaction.py)

- **`TransactionCreate`**: Reemplazar `merchant` → `name_from` + `name_destination`. Reemplazar `account_id: int` → `id_from_account: Optional[int]` + `id_destination_account: Optional[int]`. Cambiar `description` a requerido. Agregar `transaction_type: str = "expense"`.
- **`TransactionUpdate`**: Mismos cambios (todos opcionales).
- **`TransactionResponse`**: Reemplazar `merchant` → `name_from` + `name_destination`. Reemplazar `account_id` → `id_from_account` + `id_destination_account`. Agregar `transaction_type`.

#### [NEW] [debt.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/debt.py)

- `DebtCreate`: `name`, `description?`, `total_amount?`, `minimum_payment?`, `cutoff_day`, `due_day`, `interest_rate?`.
- `DebtUpdate`: todos opcionales.
- `DebtResponse`: todos los campos + `id`, `is_active`.

#### [NEW] [fixed_income.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/fixed_income.py)

- `FixedIncomeCreate`: `name`, `amount`, `frequency`, `payment_day?`, `id_destination_account`.
- `FixedIncomeUpdate`: todos opcionales.
- `FixedIncomeResponse`: todos los campos + `id`, `is_active`.
- `FixedIncomePaymentResponse`: `id`, `id_fixed_income`, `amount`, `date`, `confirmed`, `id_transaction?`.
- `ConfirmPaymentRequest`: `amount`, `date?`.

#### [MODIFY] [__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/__init__.py)

- Exportar todos los nuevos schemas de `debt` y `fixed_income`.

---

### Fase 3: Servicios (`app/services/`)

#### [MODIFY] [ai_extraction.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/services/ai_extraction.py)

- **`ensure_generic_categories()`**: Eliminar parámetro `tenant_id`. Quitar filtros por `tenant_id` e `is_active` del `select`. Quitar asignación de `tenant_id` al crear categorías.
- **`extract_transaction_data()`**: Mantener `tenant_id` en la firma (se usa en `batch_processor` para crear la `Transaction`), pero no pasarlo a `ensure_generic_categories`.
- **`ExtractionResult`**: Reemplazar `merchant` → `name_destination`. Agregar `name_from: Optional[str]`.
- **`GeminiExtractionSchema`**: Reemplazar `merchant` → `name_destination`. Agregar `name_from`.
- **`build_prompt()`**: Actualizar prompt para pedir `name_destination` (comercio/destinatario) y `name_from` (emisor, si es inferible).
- **`_build_extraction_result()`**: Actualizar para mapear los nuevos campos.

#### [MODIFY] [batch_processor.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/services/batch_processor.py)

- En `process_batch()`: Reemplazar parámetro `account_id` → `id_from_account`. Al crear `Transaction`, usar `id_from_account`, `name_from = "Usuario"` (placeholder), `name_destination = extraction.name_destination`, `description = extraction.description or extraction.name_destination`. Eliminar `merchant`.

---

### Fase 4: API Routers (`app/api/`)

#### [MODIFY] [transactions.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/transactions.py)

- **`POST /transactions`**: Crear `Transaction` con los nuevos campos (`name_from`, `name_destination`, `id_from_account`, `id_destination_account`, `transaction_type`). Eliminar `merchant` y `account_id`.
- **`POST /transactions/smart-ingest`**: Reemplazar `account_id` en Form → `id_from_account`. Mapear `extraction.name_destination` y `extraction.name_from`. Eliminar `merchant`.

#### [MODIFY] [batch.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/batch.py)

- En `POST /batch/ingest`: Reemplazar `account_id` en `Form(...)` → `id_from_account`. Pasar `id_from_account` a `process_batch()`.

#### [NEW] [debts.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/debts.py)

CRUD completo con soft delete y filtro multi-tenant:

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/debts` | Crear deuda |
| `GET` | `/api/debts` | Listar deudas activas del tenant |
| `GET` | `/api/debts/{id}` | Obtener deuda por ID |
| `PATCH` | `/api/debts/{id}` | Actualizar deuda |
| `DELETE` | `/api/debts/{id}` | Soft delete |

#### [NEW] [fixed_incomes.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/fixed_incomes.py)

CRUD completo + endpoint de confirmación de pago:

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/fixed-incomes` | Crear configuración |
| `GET` | `/api/fixed-incomes` | Listar ingresos fijos del tenant |
| `GET` | `/api/fixed-incomes/{id}` | Obtener por ID |
| `PATCH` | `/api/fixed-incomes/{id}` | Actualizar |
| `DELETE` | `/api/fixed-incomes/{id}` | Soft delete |
| `POST` | `/api/fixed-incomes/{id}/confirm-payment` | Confirmar pago → crea `FixedIncomePayment` + `Transaction` |

La lógica de `confirm-payment` crea:
1. Una `Transaction` con `name_from = "Usuario"`, `name_destination = FixedIncome.name`, `id_destination_account = FixedIncome.id_destination_account`, `transaction_type = "income"`.
2. Un `FixedIncomePayment` vinculado a la transacción.

#### [MODIFY] [__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/__init__.py)

- Exportar los nuevos routers: `debts_router`, `fixed_incomes_router`.

---

### Fase 5: Integración y Seed Data

#### [MODIFY] [main.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/main.py)

- Registrar los nuevos routers: `debts_router`, `fixed_incomes_router`.
- En el `lifespan`, llamar al seed de datos iniciales.

#### [NEW] [seed.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/db/seed.py)

- Función `run_seed(engine)` que inserte accounts y categorías base si las tablas están vacías.
- **17 Accounts** colombianos base (Bancolombia, Nequi, Daviplata, Éxito, D1, etc.) con su `type` correspondiente.
- **9 Categorías** genéricas (Alimentación, Transporte, Vivienda, etc.).
- Se ejecuta al iniciar la app en el `lifespan`.

---

### Fase 6: Migraciones y Base de Datos

1. **Eliminar** `app/data/personal_finances.db` (la BD SQLite actual).
2. **Eliminar** `app/db/migrations/versions/e9a51ffdb739_initial_schema.py` (y cualquier `__pycache__`).
3. **Generar** nueva migración inicial con todos los modelos V2:
   ```bash
   alembic revision --autogenerate -m "initial_schema_v2"
   ```
4. **Revisar** el archivo generado para validar que incluya las 7 tablas con las columnas correctas.
5. **Aplicar** la migración:
   ```bash
   alembic upgrade head
   ```
6. **Verificar** esquema:
   ```bash
   python scripts_db/query_db.py schema
   ```

---

## Resumen de archivos impactados

| Archivo | Acción | Fase |
|---|---|---|
| [financial.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/models/financial.py) | MODIFY | 1 |
| [models/__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/models/__init__.py) | MODIFY | 1 |
| [schemas/transaction.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/transaction.py) | MODIFY | 2 |
| [schemas/debt.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/debt.py) | NEW | 2 |
| [schemas/fixed_income.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/fixed_income.py) | NEW | 2 |
| [schemas/__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/schemas/__init__.py) | MODIFY | 2 |
| [ai_extraction.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/services/ai_extraction.py) | MODIFY | 3 |
| [batch_processor.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/services/batch_processor.py) | MODIFY | 3 |
| [api/transactions.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/transactions.py) | MODIFY | 4 |
| [api/batch.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/batch.py) | MODIFY | 4 |
| [api/debts.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/debts.py) | NEW | 4 |
| [api/fixed_incomes.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/fixed_incomes.py) | NEW | 4 |
| [api/__init__.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/api/__init__.py) | MODIFY | 4 |
| [main.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/main.py) | MODIFY | 5 |
| [db/seed.py](file:///c:/Users/haroldaaguilarb/source/repos/Api-finanzas-personales/app/db/seed.py) | NEW | 5 |
| `app/data/personal_finances.db` | DELETE | 6 |
| `app/db/migrations/versions/*.py` | DELETE + NEW | 6 |

---

## Verification Plan

### Automated Tests

```bash
# 1. Verificar imports de modelos
python -c "from app.models.financial import Account, Category, Transaction, BatchIngestion, Debt, FixedIncome, FixedIncomePayment; print('Models OK')"

# 2. Verificar imports de schemas
python -c "from app.schemas.debt import DebtCreate, DebtResponse; from app.schemas.fixed_income import FixedIncomeCreate, FixedIncomeResponse; print('Schemas OK')"

# 3. Verificar esquema BD
python scripts_db/query_db.py schema

# 4. Verificar seed data
python scripts_db/query_db.py query --sql "SELECT COUNT(*) FROM account"
python scripts_db/query_db.py query --sql "SELECT COUNT(*) FROM category"
```

### Manual Verification

```bash
# Arranque limpio del servidor (debe iniciar sin errores)
uvicorn app.main:app --reload

# Verificar Swagger UI en http://localhost:8000/docs
# Confirmar que aparecen los endpoints:
#   - POST/GET /transactions
#   - POST /transactions/smart-ingest
#   - POST/GET /batch
#   - POST/GET/PATCH/DELETE /debts
#   - POST/GET/PATCH/DELETE /fixed-incomes
#   - POST /fixed-incomes/{id}/confirm-payment
```
