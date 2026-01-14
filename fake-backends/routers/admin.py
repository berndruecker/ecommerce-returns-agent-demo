import logging
from fastapi import APIRouter
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.admin")

@router.post("/reset")
async def reset_demo_data():
    """Reset in-memory demo data back to initial baseline."""
    logger.info("### ADMIN ### resetDemoData ### starting reset")
    data_store.reset()
    logger.info("### ADMIN ### resetDemoData ### completed")
    return {"status": "ok", "message": "Demo data has been reset."}
