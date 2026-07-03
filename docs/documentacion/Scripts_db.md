# Scripts de Consulta a la Base de Datos

| Comando | Qué obtiene |
|---|---|
| `python scripts_db/query_db.py tables` | Lista todas las tablas con su conteo de registros |
| `python scripts_db/query_db.py txs` | Últimas 20 transacciones |
| `python scripts_db/query_db.py txs --status PendingReview` | Transacciones filtradas por estado |
| `python scripts_db/query_db.py accounts` | Cuentas bancarias/billeteras con saldo y conteo de transacciones |
| `python scripts_db/query_db.py categories` | Categorías con conteo de transacciones |
| `python scripts_db/query_db.py batches` | Lotes de procesamiento masivo con estado y conteo |
| `python scripts_db/query_db.py schema` | Esquema de todas las tablas (columnas y tipos) |
| `python scripts_db/query_db.py schema --table transaction` | Esquema de una tabla específica |
| `python scripts_db/query_db.py query --sql "SELECT * FROM account"` | SQL libre |
