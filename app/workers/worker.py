"""Railway worker entrypoint.

Run as separate Railway service when ready:
python -m app.workers.worker

It is safe to deploy now. If FUNDING_MONITOR_ENABLED=false, it idles.
"""
from __future__ import annotations
import os, time
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.services.monitoring import run_funding_monitor_once


def main():
    init_db()
    interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "21600"))  # 6 hours
    print("Mogul Grant System worker started", {"funding_monitor_enabled": settings.funding_monitor_enabled, "interval": interval})
    while True:
        if settings.funding_monitor_enabled:
            db = SessionLocal()
            try:
                result = run_funding_monitor_once(db)
                print("funding_monitor_result", result)
            except Exception as exc:
                print("funding_monitor_error", repr(exc))
            finally:
                db.close()
        time.sleep(interval)

if __name__ == "__main__":
    main()
