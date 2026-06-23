# MEMORANDO DE ARQUITECTURA Y DISEÑO: PERSONAL FINANCES MICROSERVICE

Este documento consolida la visión de producto, las decisiones tecnológicas y la estrategia de implementación acordadas para el nuevo microservicio de **Finanzas Personales (PersonalFinances)**, diseñado para integrarse de forma nativa y políglota al ecosistema de **Punto Kontable**.

---

## 1. Alineación con la Arquitectura Base

El microservicio se acoplará estrictamente a las reglas preestablecidas en el archivo maestro `DOCUMENTACION_GENERAL.md`. Aunque se desarrollará en un stack tecnológico diferente (Python), respetará el diseño gobernado por el **API Gateway** en **ASP.NET Core 9.0**:

*   **Autenticación Centralizada:** El microservicio no gestionará registros ni logins[cite: 1]. Delegará la verificación en el Gateway y consumirá el JWT Bearer Token entrante[cite: 1].
*   **Aislamiento Multi-Tenant:** Se extraerá el claim `tenantId` del token para aplicar filtros de consulta globales en la base de datos SQLite compartida, garantizando que los datos financieros estén aislados lógicamente por usuario/empresa[cite: 1].
*   **Reglas de Integridad:** Se prohíbe el borrado físico de transacciones o cuentas; se aplicará *Soft Delete* (`is_active = False`)[cite: 1]. Además, las relaciones de base de datos usarán borrado restrictivo (`Restrict`)[cite: 1].
*   **Abstracción de Datos:** Ninguna entidad de base de datos se expondrá directamente en las respuestas HTTP; se emplearán esquemas de validación estrictos (DTOs) para todas las requests y responses[cite: 1].
*   **Enrutamiento:** El tráfico será redirigido de forma transparente por el reverse proxy YARP del Gateway bajo el prefijo de ruta correspondiente[cite: 1].

---

## 2. Definición Funcional (Propuesta de Valor e Ideas de Producto)

Para resolver la fricción del registro manual de gastos (causa principal del abandono de este tipo de aplicaciones), el microservicio implementará cuatro pilares funcionales:

### A. Canal de Entrada Híbrido (Manual / Inteligente)
El sistema permitirá dos vías de registro agnósticas:
1.  **Tradicional:** Formulario manual estándar en Angular que se consolida de inmediato en la base de datos en estado `Confirmed`.
2.  **Smart Ingestion (IA):** Carga de imágenes (capturas de pantalla de Nequi, aplicaciones bancarias, fotos de recibos) o PDFs (facturas electrónicas). Un modelo de lenguaje de visión (OpenAI o modelo local vía Ollama) procesará el archivo y extraerá un JSON estructurado con: *Monto, Fecha, Comercio y Categoría sugerida*. Estos registros se guardarán en una tabla temporal en estado `PendingReview` para que el usuario los valide con un solo clic.

### B. Procesamiento por Lotes (Bulk Processing)
Para optimizar el tiempo del usuario al digitalizar múltiples recibos acumulados:
*   Se permitirá la carga masiva simultánea de **hasta un máximo de 10 archivos** por petición.
*   El backend procesará estos documentos de manera asíncrona en segundo plano para evitar congelar la interfaz, notificando al frontend Angular cuando el lote esté listo para revisión en un panel unificado.

### C. Motor de Conciliación Bancaria (El "Cruce" de Datos)
Herramienta diseñada para contrastar la "verdad absoluta" de las cuentas bancarias con los registros de la app:
*   El usuario subirá el extracto mensual en PDF o CSV (ej. Nequi o bancos tradicionales).
*   El backend mapeará los movimientos reales y ejecutará un algoritmo de emparejamiento basado en tres variables: **Monto exacto, ventana de tiempo cercana (±3 días) y similitud de texto**.
*   Clasificará los resultados en un panel interactivo: `Conciliado` (Coincidencia exitosa), `Sugerido` (Posible coincidencia que requiere aprobación manual) y `No Encontrado` (Gastos fantasma del extracto que el usuario olvidó registrar).

### D. Ventana de Análisis Inteligente (Insights)
En lugar de mostrar únicamente gráficos estadísticos planos, el sistema generará analíticas descriptivas y proactivas procesadas en lenguaje humano:
*   **Alertas de Ritmo:** Notificaciones si una tarjeta de crédito o cuenta está teniendo una velocidad de gasto (frecuencia/monto) inusualmente alta respecto al promedio del mes.
*   **Identificación de "Gastos Hormiga":** Alertas sobre el gasto recurrente más repetido del mes (ej. "Has comprado 14 veces en Uber este mes, sumando $X").
*   **Refuerzo Positivo:** Felicitaciones automatizadas cuando una categoría se mantenga significativamente por debajo del presupuesto planeado.

---

## 3. Justificación de la Arquitectura Políglota (El "Cómo")

Se determinó que la combinación de **Python (Backend)** y **Angular (Frontend)** es la ideal por las siguientes razones de ingeniería:

*   **FastAPI sobre .NET para este Microservicio:** Python posee el monopolio y la madurez de las herramientas de ciencia de datos, manipulación de archivos y SDKs de Inteligencia Artificial (OpenAI, LangChain, Pandas). FastAPI ofrece un rendimiento asíncrono excepcional para gestionar las llamadas de los modelos de IA sin bloquear los hilos del servidor, manteniendo una estructura de controladores, inyección de dependencias y documentación Swagger automática idéntica a la experiencia de ASP.NET Core 9.0[cite: 1].
*   **Visualización Eficiente de Gráficos (JSON vs Imágenes/PowerBI):** 
    *   *Descarte de Matplotlib:* Genera imágenes estáticas no interactivas, rompiendo la experiencia de usuario moderna.
    *   *Descarte de PowerBI:* Introduce costos elevados de licenciamiento (PowerBI Embedded) y dependencias pesadas en el frontend.
    *   *Estrategia Elegida:* El microservicio en Python utilizará **Pandas** exclusivamente como motor de cálculo para procesar datos duros y consumirá poca memoria. Retornará estructuras JSON limpias. El frontend en **Angular** recibirá estos objetos JSON y renderizará gráficos vectoriales e interactivos de forma nativa utilizando librerías modernas como **ApexCharts** o **Chart.js**.

---

## 4. Prompt de Orquestación Final para Generación de Código

Este es el prompt técnico unificado que se le suministrará a la IA encargada de escribir el código fuente del backend:

```markdown
Actúa como un Ingeniero de Software Senior y Arquitecto de Soluciones experto en Python, FastAPI e Inteligencia Artificial. Necesito estructurar el backend de un nuevo microservicio que se integrará a un ecosistema existente gobernado por un API Gateway en ASP.NET Core 9.0 con YARP, según las especificaciones técnicas globales del sistema (referenciadas en "DOCUMENTACION_GENERAL.md").

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