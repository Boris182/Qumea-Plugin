import logging
from fastapi import APIRouter
from .. import __version__

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Status"])

@router.get("/health")
async def health():
    logger.info("Health Status wurde aufgerufen")
    return {"status": "ok", "version": __version__}
