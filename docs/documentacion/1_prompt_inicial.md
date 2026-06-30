Actúa como un Ingeniero de Software Senior y Arquitecto de Soluciones experto en Python, FastAPI e Inteligencia Artificial. Necesito estructurar el backend de un nuevo microservicio que se integrará a un ecosistema existente gobernado por un API Gateway en ASP.NET Core 9.0 con YARP, según las especificaciones técnicas globales del sistema (referenciadas en "contexto/DOCUMENTACION_GENERAL.md").

El microservicio se llamará "PersonalFinances" (Finanzas Personales).

### 1. Stack Tecnológico Obligatorio
- Framework: FastAPI (Asíncrono, con generación automática de OpenAPI/Swagger).
- ORM/Data: SQLModel o SQLAlchemy operando sobre una base de datos SQLite compartida.
- Procesamiento de Datos: Pandas o Polars.
- Integración IA: OpenAI SDK / Ollama (para LLMs de visión locales).
- Migraciones: Alembic.

### 2. Reglas de Integración con el API Gateway (.NET 9.0)
Este microservicio se ejecuta detrás de YARP. No gestiona login directo, sino que recibe peticiones autenticadas vía JWT Bearer Token. Debe implementar un middleware o dependencia de seguridad que:
- Valide y decodifique el JWT (clave compartida).
- Extraiga los claims requeridos en "DOCUMENTACION_GENERAL.md": `tenantId` (string/UUID), `role` (string) y `modules` (lista JSON).
- Verifique la autorización: el usuario debe tener el rol "SuperAdmin" o el módulo "personal-finances" en su lista de claims.
- Inyecte el `tenantId` en el contexto de la petición para asegurar el Aislamiento Lógico Multi-Tenant en cada consulta a la base de datos.

### 3. Reglas Arquitectónicas Estrictas
- Soft Delete: Prohibido usar `DELETE` físico. Todo registro debe desactivarse usando `is_active: bool = True`.
- Integridad: Configurar las llaves foráneas con borrado restrictivo (equivalente a `DeleteBehavior.Restrict`).
- Separación de Capas: Uso estricto de Schemas de Pydantic como DTOs (Data Transfer Objects) independientes de los modelos de la base de datos. Jamás exponer entidades directas en los endpoints.

### 4. Características Principales a Implementar (Módulos Core)

#### A. Canal de Entrada Híbrido (Manual / IA)
- Registro Manual: Endpoint POST tradicional que recibe un Pydantic Schema de transacción y lo guarda directo con estado `Confirmed`.
- Registro Automatizado (Smart Ingestion): Endpoint POST que recibe un archivo (Imagen o PDF) adjunto al `tenantId`. Debe enviar el documento al modelo de visión (OpenAI/Ollama), extraer mediante Structured Outputs (JSON): Monto, Fecha, Comercio y Categoría sugerida, y guardarlo en una tabla temporal con estado `PendingReview`.

#### B. Procesamiento en Lote (Bulk Processing)
- Endpoint para carga masiva de archivos (Máximo 10 por petición).
- Debe procesar los archivos de manera asíncrona utilizando `BackgroundTasks` de FastAPI para evitar bloquear el hilo principal. El cliente recibe un ID de lote de inmediato.

#### C. Motor de Conciliación Bancaria (Cruce de Datos)
- Endpoint para cargar extractos de Nequi o bancos (PDF/CSV).
- Módulo encargado de extraer la lista de movimientos reales y compararla con las transacciones registradas usando un algoritmo de emparejamiento (monto exacto, rango de fechas ±3 días y similitud de texto).
- Retornar un JSON estructurado con tres estados: `Conciliated`, `Suggested` o `Unmatched`.

#### D. Motor de Insights (Analítica para Angular)
- Endpoint que procese el histórico del mes mediante Pandas.
- No debe renderizar imágenes de gráficos. Debe retornar datos estadísticos agregados en JSON limpios (frecuencias, porcentajes de incremento, alertas de velocidad de gasto en tarjetas, hitos de ahorro). Este JSON será consumido por librerías gráficas (como ApexCharts) en el frontend Angular.

### 5. ACCIONES DE EJECUCIÓN INMEDIATA (Requerimientos de Inicialización)
Quiero que actúes de manera autónoma sobre el entorno de desarrollo actual ejecutando los siguientes pasos paso a paso:

1. **Creación del Proyecto en la Raíz:** Inicializa la estructura completa de directorios recomendada para un proyecto profesional en FastAPI directamente en la carpeta raíz en la que te encuentras actualmente (por ejemplo, creando carpetas como `app/`, `app/models/`, `app/api/`, `app/core/`, etc.).
2. **Instalación e Inyección de Dependencias:** Genera el archivo `requirements.txt` correspondiente e instala todas las librerías necesarias ejecutando los comandos del sistema pertinentes (incluyendo `fastapi`, `uvicorn`, `sqlmodel` o `sqlalchemy`, `pydantic`, `pyjwt`, `pandas`, `alembic` y el cliente de base de datos para SQLite).
3. **Escritura de Archivos Base del Backend:** Desarrolla por completo y escribe en el disco los siguientes archivos funcionales iniciales:
    - Los modelos de base de datos base (`Account`, `Transaction`, `Category`, `BatchIngestion`) aplicando las políticas obligatorias de soft delete y multi-tenancy.
    - El módulo de seguridad / dependencia en FastAPI encargado de interceptar el JWT enviado por el Gateway, decodificarlo y extraer de forma limpia sus claims.
    - El archivo de configuración global (`config.py` o similar) para administrar variables de entorno y llaves secretas compartidas.
4. **Punto de Entrada Operativo (`main.py`):** Desarrolla el archivo principal de FastAPI que levante el servidor, configure los middlewares (como CORS), inicialice la conexión a la base de datos SQLite y exponga los primeros endpoints de prueba (salud del sistema / ping) para verificar que el microservicio pueda correr inmediatamente con `uvicorn app.main:app`.