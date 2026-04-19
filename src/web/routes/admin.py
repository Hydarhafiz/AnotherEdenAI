"""Admin routes — data refresh endpoint."""
from fastapi import APIRouter, BackgroundTasks, Depends

from ..dependencies import get_driver, verify_admin_key

router = APIRouter(prefix="/admin")


@router.post("/refresh-data")
async def refresh_data(
    background_tasks: BackgroundTasks,
    _key: str = Depends(verify_admin_key),
    driver=Depends(get_driver),
):
    """Trigger the ETL pipeline. Protected by X-Admin-Key header.

    Runs ETL directly (awaitable) passing shared driver so ETL won't close it.
    Returns {"status": "ok", "message": "ETL complete"} on success,
    or {"status": "error", "message": <error>} on failure.
    For Phase 4 the response is synchronous-enough; full async ETL is Phase 5.
    """
    from src.etl.run_etl import main as run_etl

    try:
        await run_etl(driver=driver)
        return {"status": "ok", "message": "ETL complete — data refreshed"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}
