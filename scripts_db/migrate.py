import subprocess
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_alembic(args):
    cmd = [sys.executable, "-m", "alembic"] + args
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout)
    return True

def migrate():
    if len(sys.argv) < 2:
        print("Uso: python scripts_db/migrate.py <comando> [opciones]")
        print()
        print("Comandos disponibles:")
        print("  new <descripcion>    - Crear nueva migracion (autogenerate)")
        print("  up                   - Aplicar migraciones pendientes")
        print("  down                 - Revertir ultima migracion")
        print("  current              - Ver version actual de la BD")
        print("  history              - Ver historial de migraciones")
        print("  sql <revision>       - Generar SQL de una migracion")
        return

    cmd = sys.argv[1]
    if cmd == "new":
        if len(sys.argv) < 3:
            print("Usa: python scripts_db/migrate.py new \"descripcion del cambio\"")
            return
        msg = " ".join(sys.argv[2:])
        run_alembic(["revision", "--autogenerate", "-m", msg])
    elif cmd == "up":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_alembic(["upgrade", target])
    elif cmd == "down":
        run_alembic(["downgrade", "-1"])
    elif cmd == "current":
        run_alembic(["current"])
    elif cmd == "history":
        run_alembic(["history"])
    elif cmd == "sql":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_alembic(["upgrade", revision, "--sql"])
    else:
        print(f"Comando desconocido: {cmd}")

if __name__ == "__main__":
    migrate()
