import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..db.database import get_db
from ..db.crud import rooms as rooms_crud
from ..routers.api_models import RoomDto, addRoomDto

router = APIRouter(prefix="/api/room", tags=["Rooms"])



@router.get("/", response_model=list[RoomDto])
def get_rooms(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rooms = rooms_crud.list_rooms(db)
    return rooms

@router.post("/create", response_model=RoomDto)
def create_room(
    room: addRoomDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    room = rooms_crud.create_room(db, room_name=room.room_name, ascom_device_id=room.ascom_device_id)
    return room

@router.put("/{room_id}", response_model=RoomDto)
def update_room(
    room_id: int,
    room: addRoomDto,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    updated = rooms_crud.update_room(db, room_id, room_name=room.room_name, ascom_device_id=room.ascom_device_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return updated


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    success = rooms_crud.delete_room(db, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return {"status": "success"}
