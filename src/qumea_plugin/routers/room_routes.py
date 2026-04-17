import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import csv, io
from ..deps import get_current_user
from ..db.database import get_db
from ..db.models import Room
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

### Export to CSV ###
@router.get("/export")
def export_rooms_csv(db: Session = Depends(get_db), user=Depends(get_current_user)):

    def row_generator():
        # BOM für Excel
        yield "\ufeff"
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow(["room_name", "ascom_device_id"])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)

        rooms = rooms_crud.list_rooms(db)
        for room in rooms:
            writer.writerow([
                room.room_name or "",
                room.ascom_device_id or ""
            ])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    headers = {"Content-Disposition": 'attachment; filename="rooms.csv"'}
    return StreamingResponse(row_generator(), media_type="text/csv; charset=utf-8", headers=headers)

### Import CSV to Database ###
@router.post("/import")
async def import_rooms_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Bitte eine .csv-Datei hochladen")

    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="CSV konnte nicht gelesen werden (UTF-8 erwartet)")


    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV hat keine Header-Zeile")


    headers = {h.strip(): i for i, h in enumerate(reader.fieldnames)}
    print(headers)
    required = {"room_name", "ascom_device_id"}
    if not required.issubset(headers.keys()):
        raise HTTPException(
            status_code=400,
            detail=f"CSV-Header muss enthalten: {', '.join(sorted(required))}"
        )

    try:
        rooms_crud.delete_all_rooms(db)
        rows = []
        for row in reader:
            def norm(v):
                v = (v or "").strip()
                return v or None
            obj = Room(
                room_name=norm(row.get("room_name")),
                ascom_device_id=norm(row.get("ascom_device_id")),
                )
            rows.append(obj)
        if rows:
            db.bulk_save_objects(rows)
        db.commit() 
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Import fehlgeschlagen: {e}")


    return JSONResponse({"status": "ok", "imported": len(rows)})