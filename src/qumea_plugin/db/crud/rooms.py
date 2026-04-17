from sqlalchemy.orm import Session
from ..models import Room


def list_rooms(db: Session) -> list[Room]:
    return db.query(Room).all()


def get_room(db: Session, room_id: int) -> Room | None:
    return db.query(Room).filter(Room.id == room_id).first()


def get_room_by_name(db: Session, name: str) -> Room | None:
    return db.query(Room).filter(Room.room_name == name).first()


def create_room(db: Session, *, room_name: str, ascom_device_id: str) -> Room:
    room = Room(
        room_name=room_name,
        ascom_device_id=ascom_device_id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

def create_rooms(db: Session, *, rooms: list[Room]) -> list[Room]:
    db.bulk_save_objects(rooms)
    db.commit()
    return rooms

def update_room(
    db: Session,
    room_id: int,
    *,
    room_name: str | None = None,
    ascom_device_id: str | None = None,
) -> Room | None:
    room = get_room(db, room_id)
    if not room:
        return None

    if room_name is not None:
        room.room_name = room_name
    if ascom_device_id is not None:
        room.ascom_device_id = ascom_device_id

    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int) -> bool:
    room = get_room(db, room_id)
    if not room:
        return False
    db.delete(room)
    db.commit()
    return True

def delete_all_rooms(db: Session) -> bool:
    db.query(Room).delete(synchronize_session=False)
    db.commit()
    return True
