from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/service", tags=["Service"])

@router.post("/start")
async def start_service(request: Request):
    mgr = request.app.state.service_manager
    await mgr.start()
    return mgr.get_status()

@router.post("/stop")
async def stop_service(request: Request):
    mgr = request.app.state.service_manager
    await mgr.stop()
    return mgr.get_status()

@router.get("/status")
async def service_status(request: Request):
    mgr = request.app.state.service_manager
    return mgr.get_status()

@router.get("/health")
async def health(request: Request):
    mgr = request.app.state.service_manager
    # “health” = API lebt. Status zeigt, ob Worker laufen.
    return {"ok": True, **mgr.get_status()}
