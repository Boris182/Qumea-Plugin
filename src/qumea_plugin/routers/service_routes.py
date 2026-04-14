from fastapi import APIRouter, Request, HTTPException, Depends
from qumea_plugin.deps import get_current_user

router = APIRouter(prefix="/api/service", tags=["Service"])

@router.post("/start")
async def start_service(request: Request, user=Depends(get_current_user)):
    mgr = request.app.state.service_manager
    await mgr.start()
    return mgr.get_status()

@router.post("/stop")
async def stop_service(request: Request, user=Depends(get_current_user)):
    mgr = request.app.state.service_manager
    await mgr.stop()
    return mgr.get_status()

@router.get("/status")
async def service_status(request: Request, user=Depends(get_current_user)):
    mgr = request.app.state.service_manager
    return mgr.get_status()

@router.get("/health")
async def health(request: Request, user=Depends(get_current_user)):
    mgr = request.app.state.service_manager
    return {"ok": True, **mgr.get_status()}

