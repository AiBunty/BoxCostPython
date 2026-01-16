"""
Background job scheduling endpoints (lightweight placeholder).
Future: integrate with Celery/RQ/Arq.
"""
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends

from backend.middleware.auth import get_current_user
from backend.services.cache_service import cache_service
from backend.routers.realtime import manager
from backend.models.user import User

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def _simulate_job(name: str):
    # Placeholder for real job enqueue; update cache to simulate work result.
    result = {"job": name, "status": "completed", "completed_at": datetime.utcnow().isoformat()}
    cache_service.set(f"job:{name}:result", result, ttl_seconds=3600)
    return result


@router.post("/rebuild-reports")
def rebuild_reports(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """
    Enqueue a reports rebuild job and notify listeners.
    """
    def _task():
        result = _simulate_job("rebuild-reports")
        try:
            import asyncio
            asyncio.run(manager.broadcast({"type": "job:completed", "job": "rebuild-reports", "timestamp": result["completed_at"]}))
        except Exception:
            pass
        return result

    background_tasks.add_task(_task)
    return {"message": "Report rebuild enqueued"}


@router.get("/status/{job_name}")
def job_status(job_name: str, current_user: User = Depends(get_current_user)):
    """
    Fetch a simple cached job result.
    """
    result = cache_service.get(f"job:{job_name}:result")
    if result:
        return result
    return {"job": job_name, "status": "pending"}
