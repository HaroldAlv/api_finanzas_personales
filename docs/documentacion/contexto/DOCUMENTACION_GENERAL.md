# API Gateway — Punto Kontable

Documentación general de contexto para agentes de IA.

## 1. Visión General

API Gateway desarrollado en **ASP.NET Core 9.0** que actúa como punto de entrada único para un shell en Angular. Tiene dos responsabilidades fundamentales:

1. **Autenticación centralizada** — Emitir JWTs y gestionar sesiones mediante HttpOnly cookies.
2. **Reverse Proxy (YARP)** — Redirigir tráfico del shell hacia micro-backends y micro-frontends.

## 2. Stack Tecnológico

| Tecnología | Versión | Propósito |
|---|---|---|
| ASP.NET Core | 9.0 | Framework base |
| SQLite + EF Core | 9.x | Persistencia de datos |
| YARP | 2.3.0 | Reverse Proxy |
| JWT Bearer | 9.0.0 | Autenticación |
| BCrypt.Net-Next | 4.x | Hash de contraseñas |
| Swashbuckle | 10.2.1 | Documentación Swagger |

## 3. Estructura del Proyecto

```
ApiGateway/
├── ApiGateway.sln
├── prompt/                               ← Documentación y prompts de especificación
│   ├── 1_promp-gateway.md
│   ├── 2_CONTEXTO_PROYECTO.md
│   ├── 3_sqlite-multitenant.md
│   ├── 4_endpoint-refresh-backend.md
│   ├── 5_refresh-endpoint-implementado.md
│   └── contexto/
│       └── DOCUMENTACION_GENERAL.md      ← Este archivo
├── ApiGateway/
│   ├── Program.cs                        ← Pipeline: CORS → Auth → YARP
│   ├── appsettings.json                  ← Config JWT + YARP Routes/Clusters
│   ├── appsettings.Development.json
│   ├── ApiGateway.http                   ← Endpoints de prueba
│   │
│   ├── Controllers/
│   │   ├── AuthController.cs             ← POST /api/auth/login, refresh, logout
│   │   ├── Admin/
│   │   │   ├── TenantsController.cs
│   │   │   ├── UsersController.cs
│   │   │   ├── PlansController.cs
│   │   │   ├── ModulesController.cs
│   │   │   └── TenantPlansController.cs
│   │   └── WeatherForecastController.cs  ← (artifact de plantilla)
│   │
│   ├── Models/
│   │   ├── LoginRequest.cs
│   │   ├── LoginResponse.cs
│   │   ├── User.cs
│   │   ├── Tenant.cs
│   │   ├── Module.cs
│   │   ├── Plan.cs
│   │   ├── PlanModule.cs
│   │   ├── TenantPlan.cs
│   │   ├── RefreshToken.cs
│   │   └── DTOs/                         ← DTOs de request/response para Admin
│   │
│   ├── Services/
│   │   ├── IUserService.cs               ← Interfaz para gestión de usuarios
│   │   ├── EfUserService.cs              ← Implementación con EF Core
│   │   ├── ITokenService.cs              ← Interfaz para generación de tokens y refresh
│   │   └── TokenService.cs               ← Implementación JWT + Refresh Tokens
│   │
│   ├── Data/
│   │   └── AppDbContext.cs               ← DbContext de EF Core
│   │
│   ├── Properties/
│   │   └── launchSettings.json           ← Perfiles: http (5026), https (7071), IIS Express
│   │
│   ├── Migrations/                       ← Migraciones EF Core
│   ├── bin/
│   └── obj/
```

## 4. Pipeline HTTP (orden en Program.cs)

```
1. CORS
2. Autenticación JWT
3. Autorización
4. Controladores (API)
5. YARP Reverse Proxy
```

## 5. Autenticación y Sesión

### 5.1 Login — `POST /api/auth/login`

- **Request:** `{ "email": "...", "password": "..." }`
- **Response:** `{ "token": "eyJ...", "expiration": "2026-..." }`
- **Adicional:** Setea HttpOnly cookie `pk_refresh_token`
- Validación contra SQLite mediante `EfUserService` (BCrypt)

#### Claims del JWT

| Claim | Valor |
|---|---|
| `sub` | email del usuario |
| `jti` | GUID único |
| `email` | email |
| `role` | `SuperAdmin` \| `Admin` \| `User` |
| `tenantId` | id del tenant (vacío si SuperAdmin) |
| `modules` | array JSON de keys de módulos habilitados (`["*"]` para SuperAdmin) |

### 5.2 Refresh — `POST /api/auth/refresh`

- **No requiere** `Authorization` header ni body
- Lee la cookie `pk_refresh_token` automáticamente enviada por el navegador
- Cookie válida → `200 OK` con nuevo `{ token, expiration }` + nueva cookie rotada
- Cookie inválida/ausente → `401 Unauthorized`

### 5.3 Logout — `POST /api/auth/logout`

- **No requiere** `Authorization` header ni body
- Revoca el refresh token en BD y elimina la cookie
- Siempre retorna `200 OK`

### 5.4 Configuración de Cookies

| Propiedad | Valor |
|---|---|
| Nombre | `pk_refresh_token` |
| HttpOnly | `true` |
| Secure | `true` |
| SameSite | `SameSiteMode.None` |
| Path | `/` |
| MaxAge | 7 días |
| JWT expiration | 30 minutos |
| Refresh rotation | Sí (se revoca al usar `/refresh`) |

## 6. Modelo Multi-Tenant

La base de datos utiliza el enfoque de **Base de Datos Compartida con Aislamiento Lógico** mediante `TenantId`.

### 6.1 Entidades

| Entidad | Descripción |
|---|---|
| **Tenant** | Empresa/cliente que contrata el servicio SaaS |
| **User** | Usuario con credenciales (BCrypt), FK a Tenant (nullable para SuperAdmin) |
| **Module** | Funcionalidad del sistema (ej: invoicing, inventory, payroll) |
| **Plan** | Paquete comercial (ej: Starter, Professional, Enterprise) |
| **PlanModule** | Unión muchos-a-muchos entre Plan y Module |
| **TenantPlan** | Historial de suscripciones de un Tenant a un Plan |
| **RefreshToken** | Token de refresco persistente con rotación y revocación |

### 6.2 Reglas de Integridad

- **Soft delete**: toda desactivación usa `IsActive = false`, nunca `DELETE` físico
- **`DeleteBehavior.Restrict`**: evita borrados en cascada no deseados
- **Índice único compuesto**: `User.Email` único por `TenantId`
- **DTOs separados**: nunca se exponen entidades directamente, `User.Password` jamás en responses

## 7. Controladores Admin (SuperAdmin)

Todos bajo `[Authorize(Roles = "SuperAdmin")]` y prefijo `/api/admin/`:

| Controlador | Endpoints |
|---|---|
| **TenantsController** | CRUD de tenants (crear con planId, soft delete) |
| **UsersController** | CRUD de usuarios con asignación a tenant |
| **PlansController** | CRUD de planes con módulos asociados |
| **ModulesController** | CRUD de módulos del sistema |
| **TenantPlansController** | Asignar/actualizar plan a un tenant |

## 8. YARP Reverse Proxy

| Ruta | Destino |
|---|---|
| `/api/users/{**catch-all}` | `http://localhost:5001` |
| `/api/products/{**catch-all}` | `http://localhost:5002` |
| `/mfe/dashboard/{**catch-all}` | `http://localhost:4201` |

## 9. Seed Data

Al iniciar por primera vez, se crea automáticamente vía migraciones:

**Módulos:**
- `invoicing` — Facturación
- `inventory` — Inventario
- `payroll` — Nómina
- `reports` — Reportes
- `crm` — CRM

**Planes:**
- **Starter** — Solo `invoicing`
- **Professional** — `invoicing` + `inventory` + `reports`
- **Enterprise** — Todos los módulos

**SuperAdmin:**
- Email: `superadmin@puntoKontable.com`
- Password: `SuperAdmin2025!` (hasheada con BCrypt)
- Role: `SuperAdmin`
- Sin tenant asignado

## 10. Reglas Arquitectónicas Clave

1. **Aislamiento por TenantId** — Toda consulta operativa debe filtrar por `TenantId` del JWT, salvo SuperAdmin.
2. **Passwords siempre BCrypt** — Nunca en texto plano. Usar `BCrypt.Net.BCrypt.HashPassword()` y `BCrypt.Verify()`.
3. **No borrado físico** — Usar `IsActive = false` para desactivación de registros.
4. **`Database.Migrate()`** — No usar `EnsureCreated()` para mantener control de esquema.
5. **DTOs separados de entidades** — Nunca exponer entidades directamente en los controladores.
6. **Rotación de refresh tokens** — Cada uso de `/refresh` invalida el token anterior y emite uno nuevo.
7. **No modificar CORS ni YARP** — Ya están configurados para el shell Angular y no deben cambiarse.
