# Migraciones con Alembic — PersonalFinances

## 1. Contexto

El proyecto usa **SQLite** como base de datos local (imposibilidad de tener MySQL/SQL Server en el entorno) y **SQLModel** como ORM. Las migraciones se gestionan con **Alembic** para mantener un control de versiones del esquema y permitir una futura migración a MySQL cambiando únicamente la URL de conexión.

### Stack

| Componente | Versión |
|---|---|
| SQLite | 3.x (built-in Python) |
| SQLModel | 0.x (SQLAlchemy wrapper) |
| Alembic | 1.18.4 |

---

## 2. Ubicación de la Base de Datos

```
Api-finanzas-personales/
└── app/
    └── data/
        └── personal_finances.db
```

Configurado en `app/core/config.py`:

```python
DATABASE_URL: str = "sqlite:///./app/data/personal_finances.db"
```

La ruta es relativa al directorio desde donde se ejecuta `uvicorn` (usualmente la raíz del proyecto).

---

## 3. Estructura de Migraciones

```
Api-finanzas-personales/
├── alembic.ini                         ← Configuración de Alembic
└── app/
    └── db/
        └── migrations/
            ├── env.py                  ← Entorno de Alembic (conecta con la app)
            ├── script.py.mako          ← Template para generar migraciones
            ├── README
            └── versions/
                └── e9a51ffdb739_initial_schema.py  ← Migración inicial
```

### `alembic.ini`

```ini
[alembic]
script_location = app/db/migrations
prepend_sys_path = .
sqlalchemy.url =                      # Se configura en env.py
```

### `app/db/migrations/env.py`

Configurado para usar el `engine` y `SQLModel.metadata` del proyecto:

```python
from sqlmodel import SQLModel
from app.models import financial      # Registra los modelos en metadata
from app.core.config import settings
from app.db.database import engine

target_metadata = SQLModel.metadata

def run_migrations_online():
    connectable = engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()
```

---

## 4. Flujo de Trabajo Diario

### 4.1 Modificar un modelo

Editas el archivo `app/models/financial.py` (agregar/eliminar columnas, relaciones, tablas).

### 4.2 Generar migración

```bash
# Opción A — usando el helper
python scripts_db/migrate.py new "descripcion del cambio"

# Opción B — directamente con Alembic
alembic revision --autogenerate -m "descripcion del cambio"
```

Esto genera un archivo en `app/db/migrations/versions/` con el SQL necesario para sincronizar la BD con los modelos.

> **Importante:** Revisar el archivo generado antes de aplicarlo. Alembic autogenerate no es perfecto y puede requerir ajustes manuales (ej. detección de `nullable`, cambios de tipo, etc.).

### 4.3 Aplicar migración

```bash
# Opción A — helper
python scripts_db/migrate.py up

# Opción B — Alembic directo
alembic upgrade head
```

### 4.4 Revertir migración

```bash
# Revertir la última
python scripts_db/migrate.py down

# O directamente
alembic downgrade -1
```

### 4.5 Consultar estado

```bash
python scripts_db/migrate.py current   # Versión actual
python scripts_db/migrate.py history   # Historial completo
```

---

## 5. Script Helper (`scripts_db/migrate.py`)

Comandos disponibles:

| Comando | Descripción |
|---|---|
| `python scripts_db/migrate.py new "mensaje"` | Crear nueva migración autogenerada |
| `python scripts_db/migrate.py up` | Aplicar migraciones pendientes |
| `python scripts_db/migrate.py up <revision>` | Migrar a una revisión específica |
| `python scripts_db/migrate.py down` | Revertir la última migración |
| `python scripts_db/migrate.py current` | Ver versión actual de la BD |
| `python scripts_db/migrate.py history` | Ver historial completo |
| `python scripts_db/migrate.py sql` | Generar SQL sin aplicarlo |

---

## 6. Script de Consulta (`scripts_db/query_db.py`)

Comandos disponibles:

| Comando | Descripción |
|---|---|
| `python scripts_db/query_db.py tables` | Listar tablas con conteo de registros |
| `python scripts_db/query_db.py txs` | Últimas transacciones |
| `python scripts_db/query_db.py txs --status PendingReview` | Filtrar por estado |
| `python scripts_db/query_db.py accounts` | Ver cuentas (con conteo de transacciones) |
| `python scripts_db/query_db.py categories` | Ver categorías (con conteo de transacciones) |
| `python scripts_db/query_db.py batches` | Ver lotes procesados |
| `python scripts_db/query_db.py schema` | Esquema de todas las tablas |
| `python scripts_db/query_db.py schema --table transaction` | Esquema de una tabla |
| `python scripts_db/query_db.py query --sql "SELECT * FROM account"` | SQL libre |

---

## 7. Modelos Actuales

### Tablas en la BD

| Tabla | Columnas clave |
|---|---|
| **account** | `id`, `name`, `balance`, `tenant_id`, `is_active` |
| **category** | `id`, `name`, `description`, `tenant_id`, `is_active` |
| **transaction** | `id`, `amount`, `date`, `merchant`, `description`, `source`, `status`, `original_file_path`, `account_id`, `category_id`, `batch_id`, `tenant_id`, `is_active` |
| **batchingestion** | `id`, `status`, `file_count`, `total_processed`, `total_failed`, `created_at`, `completed_at`, `tenant_id`, `is_active` |
| **alembic_version** | `version_num` (control interno de Alembic) |

### Reglas arquitectónicas

- **Soft delete:** todas las tablas tienen `is_active: bool = True`. Nunca se usa `DELETE` físico.
- **Multi-tenant:** todas las tablas tienen `tenant_id: str`. Toda consulta filtra por este campo.
- **Restrict:** las foreign keys usan `ondelete="RESTRICT"` para evitar borrados en cascada no deseados.

---

## 8. Migración a MySQL (Futuro)

Cuando sea necesario migrar a MySQL, solo se cambia la URL en `config.py`:

```python
# De:
DATABASE_URL: str = "sqlite:///./app/data/personal_finances.db"

# A:
DATABASE_URL: str = "mysql+pymysql://usuario:password@host:3306/personal_finances"
```

Las migraciones de Alembic son independientes del motor de BD, por lo que el historial de migraciones se re-aplica sin cambios en el código.

### Consideraciones de portabilidad

| Aspecto | SQLite | MySQL | Compatible |
|---|---|---|---|
| Auto-incremento | `INTEGER PRIMARY KEY` | `INT AUTO_INCREMENT` | Sí (SQLAlchemy abstrae) |
| Booleanos | 0/1 | TINYINT(1) / BOOL | Sí |
| DateTime | Sin zona horaria | Sin zona horaria | Sí |
| JSON | No nativo | `JSON` nativo | Usar `sa.Text` para portabilidad |
| Foreign Keys | Se habilitan con `PRAGMA` | Nativo | Sí |
| VARCHAR | Sin límite real | Con límite | Sí (SQLModel usa `AutoString`) |

---

## 9. Referencia Rápida

```bash
# Después de modificar app/models/financial.py:

python scripts_db/migrate.py new "agrega campo X a Y"   # 1. Generar
python scripts_db/migrate.py up                           # 2. Aplicar
python scripts_db/query_db.py schema --table transaction  # 3. Verificar
```
