from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine
from app.models import Base

from scripts.migrate_approval_constraints import (
    main as migrate_approval_constraints,
)
from scripts.migrate_approval_execution_claim import (
    main as migrate_approval_execution_claim,
)
from scripts.migrate_audit_append_only import (
    main as migrate_audit_append_only,
)


Base.metadata.create_all(bind=engine)

migrate_approval_execution_claim()
migrate_approval_constraints()
migrate_audit_append_only()

print("Database schema initialized successfully.")