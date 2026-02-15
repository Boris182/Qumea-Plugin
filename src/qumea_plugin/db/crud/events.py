
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import Event, EventStageRun, StageStatus, EventStatus


def confirm_via_ssh(db: Session, room_name: str, alert_type: str) -> int:
    now = datetime.utcnow()

    # Events die warten
    events = db.query(Event).filter(
        and_(
            Event.room_name == room_name,
            Event.alert_type == alert_type,
            Event.status == EventStatus.WAITING.value,
        )
    ).all()

    if not events:
        return 0

    event_ids = [e.id for e in events]

    # StageRuns auf OK setzen
    stage_runs = db.query(EventStageRun).filter(
        and_(
            EventStageRun.event_id.in_(event_ids),
            EventStageRun.stage_name == "wait_ssh_confirm",
            EventStageRun.status == StageStatus.WAITING.value,
        )
    ).all()

    for s in stage_runs:
        s.status = StageStatus.OK.value
        s.finished_at = now
        s.updated_at = now

    # Events abschließen
    for e in events:
        e.status = EventStatus.DONE.value
        e.updated_at = now

    db.commit()
    return len(stage_runs)