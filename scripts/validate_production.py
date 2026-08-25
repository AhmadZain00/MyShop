
from pathlib import Path
import ast
import importlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

required = [
    "app/main.py",
    "app/config.py",
    "app/database/connection.py",
    "app/database/models.py",
    "app/database/migrations.py",
    "app/services/auth_service.py",
    "app/services/security.py",
    "app/services/product_service.py",
    "app/services/stock_service.py",
    "app/services/excel_service.py",
    "app/services/backup_service.py",
    "app/services/database_service.py",
    "app/services/production.py",
    "app/ui/main_window.py",
    "requirements.txt",
    "MyShop.spec",
    "installer/MyShop.iss",
]

errors = []

for rel in required:
    p = ROOT / rel
    if not p.exists():
        errors.append(f"MISSING: {rel}")

for p in (ROOT / "app").rglob("*.py"):
    try:
        ast.parse(p.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"SYNTAX: {p.relative_to(ROOT)} -> {exc}")

imports = [
    "app.database.models",
    "app.database.connection",
    "app.services.security",
    "app.services.product_service",
    "app.services.stock_service",
    "app.services.excel_service",
    "app.services.backup_service",
    "app.services.database_service",
    "app.services.production",
]

for name in imports:
    try:
        importlib.import_module(name)
    except Exception as exc:
        errors.append(f"IMPORT: {name} -> {exc}")

if errors:
    print("PRODUCTION VALIDATION FAILED")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print("PRODUCTION VALIDATION PASSED")
print(f"Checked Python files under: {ROOT / 'app'}")
print(f"Checked required deployment files: {len(required)}")
