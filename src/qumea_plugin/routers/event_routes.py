import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..db.database import get_db
from ..db.crud import events as events_crud
from ..routers.api_models import EventDto

router = APIRouter(prefix="/api/event", tags=["Events"])



@router.get("/events", response_model=list[EventDto])
def get_events(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    events = events_crud.list_events(db)
    return events


@router.get("/event/{event_id}", response_model=EventDto)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    event = events_crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")
    return event


@router.delete("/event/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    success = events_crud.delete_event(db, event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event nicht gefunden")
    return {"status": "success"}

# Alle Events auf Beendet setzen
@router.get("/clear_evenents")
def clear_events(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    success = events_crud.clear_events(db)
    if not success:        
        raise HTTPException(status_code=500, detail="Fehler beim Bereinigen der Events")
    return {"status": "success"}