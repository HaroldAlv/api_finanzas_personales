import sqlite3
import argparse
import json
from datetime import datetime

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "app", "data", "personal_finances.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def list_tables():
    conn = get_conn()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print("Tablas en la base de datos:")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM \"{t['name']}\"").fetchone()[0]
        print(f"  - {t['name']}: {count} registros")
    conn.close()

def show_schema(table=None):
    conn = get_conn()
    if table:
        tables = [{"name": table}]
    else:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    for t in tables:
        print(f"\n=== {t['name']} ===")
        cols = conn.execute(f"PRAGMA table_info(\"{t['name']}\")").fetchall()
        for c in cols:
            print(f"  {c['name']:25s} {c['type']:15s} {'PK' if c['pk'] else '  '} {'NOT NULL' if not c['notnull'] else '         '}")
    conn.close()

def query(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params or ())
        rows = cur.fetchall()
        if not rows:
            print("(no results)")
        for r in rows:
            row_dict = dict(r)
            for k, v in row_dict.items():
                if isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
            print(json.dumps(row_dict, indent=2, default=str))
            print("-" * 40)
        print(f"\n{len(rows)} fila(s) retornada(s)")
    except sqlite3.Error as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def show_transactions(limit=20, status=None):
    sql = 'SELECT * FROM "transaction" WHERE 1=1'
    params = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("(no transactions)")
    for r in rows:
        d = dict(r)
        print(f"ID={d['id']:3d} | ${d['amount']:>8.2f} | {d['merchant']:25s} | {d['status']:15s} | source={d['source']:16s} | tenant={d['tenant_id']}")
    print(f"\n{len(rows)} transaccion(es)")
    conn.close()

def show_accounts(limit=20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, (SELECT COUNT(*) FROM "transaction" t WHERE (t.id_from_account = a.id OR t.id_destination_account = a.id) AND t.is_active = 1) as tx_count
        FROM "account" a
        ORDER BY a.id DESC LIMIT ?
    """, (limit,)).fetchall()
    if not rows:
        print("(no accounts)")
    for r in rows:
        d = dict(r)
        print(f"ID={d['id']:3d} | {d['name']:25s} | {d['type']:16s} | txs={d['tx_count']:3d}")
    conn.close()

def show_categories(limit=20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*, (SELECT COUNT(*) FROM "transaction" t WHERE t.category_id = c.id AND t.is_active = 1) as tx_count
        FROM "category" c
        ORDER BY c.id DESC LIMIT ?
    """, (limit,)).fetchall()
    if not rows:
        print("(no categories)")
    for r in rows:
        d = dict(r)
        print(f"ID={d['id']:3d} | {d['name']:25s} | {d.get('description', '') or '':30s} | txs={d['tx_count']:3d}")
    conn.close()

def show_batches(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT b.*, (SELECT COUNT(*) FROM "transaction" t WHERE t.batch_id = b.id) as tx_count
        FROM "batchingestion" b
        ORDER BY b.id DESC LIMIT ?
    """, (limit,)).fetchall()
    if not rows:
        print("(no batches)")
    for r in rows:
        d = dict(r)
        print(f"Batch ID={d['id']:3d} | status={d['status']:20s} | files={d['file_count']} | processed={d['total_processed']} | failed={d['total_failed']} | txs={d['tx_count']}")
    conn.close()

def run():
    parser = argparse.ArgumentParser(description="Query personal_finances.db")
    parser.add_argument("action", nargs="?", default="tables",
                        choices=["tables", "schema", "query", "txs", "batches", "accounts", "categories"],
                        help="Accion a ejecutar")
    parser.add_argument("--sql", help="SQL query personalizada")
    parser.add_argument("--table", help="Mostrar esquema de una tabla especifica")
    parser.add_argument("--limit", type=int, default=20, help="Limite de filas (default: 20)")
    parser.add_argument("--status", help="Filtrar transacciones por status")

    args = parser.parse_args()

    if args.action == "tables":
        list_tables()
    elif args.action == "schema":
        show_schema(args.table)
    elif args.action == "query":
        if not args.sql:
            print("Usa --sql con tu consulta")
            return
        query(args.sql)
    elif args.action == "txs":
        show_transactions(args.limit, args.status)
    elif args.action == "accounts":
        show_accounts(args.limit)
    elif args.action == "categories":
        show_categories(args.limit)
    elif args.action == "batches":
        show_batches(args.limit)

if __name__ == "__main__":
    run()
