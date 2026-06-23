# PersonalFinances Microservice Implementation Plan

This plan details the steps to initialize and build the "PersonalFinances" microservice in Python using FastAPI, adhering to the architecture described in `prompt_inicial.md` and the gateway documentation in `DOCUMENTACION_GENERAL.md`.

## Goal Description
Create a new FastAPI microservice named "PersonalFinances" that integrates with the existing ASP.NET Core 9.0 API Gateway (YARP). The microservice will handle multi-tenant financial data, enforce soft-delete, and include endpoints for smart ingestion, bulk processing, reconciliation, and analytics. 

This plan focuses on the **Immediate Execution Actions** required to initialize the project, set up the base structure, models, security middlewares, and the main entry point.

> [!IMPORTANT]
> **User Review Required**
> Please review this plan to confirm that the chosen libraries (SQLModel vs SQLAlchemy, OpenAI vs Ollama) and structure align with your environment before execution.

## Open Questions
> [!WARNING]
> 1. Do you prefer **SQLModel** or standard **SQLAlchemy** for the ORM? (I will plan with SQLModel for simplicity and native Pydantic integration, but let me know if you prefer SQLAlchemy).
> 2. Are you using `venv` or `conda` for environment management? I will assume a standard Python virtual environment or system-wide pip if not specified.
> 3. Should I configure the local SQLite database in the root folder or a specific `data/` directory?

## Proposed Changes

### 1. Project Setup & Dependencies
Create the root directory structure and the `requirements.txt` file.

#### [NEW] `requirements.txt`
Dependencies to install:
- `fastapi`
- `uvicorn`
- `sqlmodel` (or `sqlalchemy`)
- `pydantic`
- `pydantic-settings`
- `pyjwt`
- `pandas`
- `alembic`

### 2. Core Configurations

#### [NEW] `app/core/config.py`
Settings management using `pydantic-settings` to handle environment variables, secret keys for JWT decoding, and database URLs.

#### [NEW] `app/core/security.py`
Middleware/Dependency for FastAPI to:
- Extract JWT from `Authorization` header.
- Decode JWT using the shared secret.
- Extract `tenantId`, `role`, and `modules`.
- Enforce authorization: Verify role is `SuperAdmin` OR `modules` contains `personal-finances`.

### 3. Database & Models

#### [NEW] `app/db/database.py`
Engine initialization and session dependency (`get_session`) for SQLite.

#### [NEW] `app/models/base.py`
Base classes containing the multi-tenant (`tenant_id`) and soft-delete (`is_active`) fields required by the architecture.

#### [NEW] `app/models/financial.py`
Database entities using SQLModel:
- `Account`
- `Category`
- `Transaction`
- `BatchIngestion`
All will implement the strict architectural rules (Soft Delete, Restrict delete behavior).

### 4. Entry Point

#### [NEW] `app/main.py`
The FastAPI application factory:
- Initialize `app = FastAPI()`.
- Configure CORS.
- Setup database on startup.
- Include a simple `/ping` or `/health` endpoint to verify the service runs correctly.

## Verification Plan

### Automated Tests
- No automated tests are planned for this initialization phase, but `uvicorn` will be used to ensure the server starts without errors.

### Manual Verification
- Run `pip install -r requirements.txt`.
- Start the server using `uvicorn app.main:app --reload`.
- Send a request to `/health` to verify the application is responding.
- Verify that the SQLite `.db` file is successfully generated.
