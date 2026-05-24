from datetime import datetime, timezone
from pathlib import Path
import json

BACKUP_DIR = Path("storage/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def write_metadata_backup(name: str, payload: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"{name}_{ts}.json"
    path.write_text(json.dumps(payload, default=str, indent=2))
    return str(path)
