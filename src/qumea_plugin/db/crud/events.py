
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import Event, EventStatus

def list_events(db: Session) -> list[Event]:
    return db.query(Event).all()


def get_event(db: Session, event_id: int) -> Event | None:
    return db.query(Event).filter(Event.id == event_id).first()


def delete_event(db: Session, id: int) -> bool:
    event = get_event(db, id)
    if not event:
        return False
    db.delete(event)
    db.commit()
    return True