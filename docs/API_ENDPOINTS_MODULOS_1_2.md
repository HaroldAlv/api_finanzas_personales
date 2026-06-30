# API Endpoints — Módulos 1 y 2

Esta documentación describe los endpoints disponibles para el Frontend (Angular) referentes a los Módulos de **Canal de Entrada Híbrido** y **Procesamiento por Lotes**.

Todos los endpoints requieren autenticación (JWT Bearer Token enviado desde el Gateway) y operan de forma multi-tenant automática basada en el claim `tenantId`.

---

## 1. Módulo A — Canal de Entrada Híbrido

### 1.1 Registro Manual de Transacción

Permite crear una transacción manualmente que quedará automáticamente confirmada.

- **Método:** `POST`
- **Ruta:** `/api/transactions`
- **Body (JSON):**
```json
{
  "amount": 150.50,
  "date": "2026-06-24T00:00:00",
  "merchant": "Supermercado X",
  "description": "Compra semanal",
  "account_id": 1,
  "category_id": 5
}
```

- **Respuesta Exitosa (200 OK):**
```json
{
  "id": 1,
  "amount": 150.5,
  "date": "2026-06-24T00:00:00",
  "merchant": "Supermercado X",
  "description": "Compra semanal",
  "status": "Confirmed",
  "source": "manual",
  "account_id": 1,
  "category_id": 5,
  "batch_id": null,
  "is_active": true
}
```

### 1.2 Smart Ingestion (Extracción IA)

Permite subir una foto o PDF de un recibo. La IA extraerá los datos y la transacción se guardará como pendiente de revisión (`PendingReview`). Si el tenant no tiene categorías configuradas, el sistema creará un listado de categorías genéricas automáticamente la primera vez.

- **Método:** `POST`
- **Ruta:** `/api/transactions/smart-ingest`
- **Content-Type:** `multipart/form-data`
- **Body (Form Data):**
  - `account_id` (Integer)
  - `file` (File: PNG, JPEG o PDF, Máximo 10MB)

- **Respuesta Exitosa (200 OK):**
```json
{
  "transaction": {
    "id": 2,
    "amount": 45.0,
    "date": "2026-06-23T00:00:00",
    "merchant": "Restaurante Y",
    "description": "Almuerzo",
    "status": "PendingReview",
    "source": "smart_ingestion",
    "account_id": 1,
    "category_id": 1,
    "batch_id": null,
    "is_active": true
  },
  "ai_confidence": 0.95,
  "raw_extraction": {
    "amount": 45.0,
    "date": "2026-06-23",
    "merchant": "Restaurante Y",
    "description": "Almuerzo",
    "suggested_category": "Alimentación",
    "confidence": 0.95
  },
  "message": "Archivo procesado correctamente."
}
```

### 1.3 Listar Transacciones

- **Método:** `GET`
- **Ruta:** `/api/transactions?status=PendingReview`
- **Query Params:**
  - `status` (Opcional): Filtra por estado (ej. `PendingReview`, `Confirmed`).

### 1.4 Confirmar Transacción

Cambia el estado de una transacción extraída por IA o lote de `PendingReview` a `Confirmed`.

- **Método:** `PATCH`
- **Ruta:** `/api/transactions/{tx_id}/confirm`

### 1.5 Eliminar Transacción (Soft Delete)

Desactiva una transacción (`is_active = False`). No la borra físicamente.

- **Método:** `DELETE`
- **Ruta:** `/api/transactions/{tx_id}`

---

## 2. Módulo B — Procesamiento por Lotes

### 2.1 Carga Masiva (Bulk Ingest)

Envía hasta 10 archivos para ser procesados de manera asíncrona en segundo plano. Retorna un ID de lote inmediatamente sin bloquear la UI.

- **Método:** `POST`
- **Ruta:** `/api/batch/ingest`
- **Content-Type:** `multipart/form-data`
- **Body (Form Data):**
  - `account_id` (Integer)
  - `files` (Múltiples archivos: PNG, JPEG o PDF. Máximo 10 archivos por request).

- **Respuesta Exitosa (200 OK):**
```json
{
  "batch_id": 1,
  "file_count": 5,
  "status": "Processing",
  "message": "Lote en procesamiento."
}
```

### 2.2 Consultar Estado del Lote

Permite hacer polling del progreso del lote y ver las transacciones generadas.

- **Método:** `GET`
- **Ruta:** `/api/batch/{batch_id}`

- **Respuesta Exitosa (200 OK):**
```json
{
  "batch_id": 1,
  "status": "Completed", 
  "file_count": 5,
  "total_processed": 5,
  "total_failed": 0,
  "created_at": "2026-06-24T10:00:00",
  "completed_at": "2026-06-24T10:01:00",
  "transactions": [
    {
      "id": 3,
      "amount": 20.0,
      "merchant": "Transporte Z",
      "status": "PendingReview",
      "source": "bulk",
      "...": "..."
    }
    // ...
  ]
}
```
*(Nota: `status` puede ser `Processing`, `Completed`, `PartiallyCompleted`, o `Failed`)*.
