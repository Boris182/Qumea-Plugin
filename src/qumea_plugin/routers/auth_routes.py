from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..config import get_settings
from ..deps import get_current_user
from ..db.database import get_db
from ..db.models import User
from ..security import crypt_password, verify_password, create_access_token
from .api_models import UserRegister, UserLogin
import logging

settings = get_settings()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

@router.post("/register", description="Register a new user account.")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).first():
        raise HTTPException(status_code=403, detail="Login existiert bereits")
    db_user = User(username=user.username, hashed_password=crypt_password(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return JSONResponse(status_code=201, content={"message": "Registrierung erfolgreich"})


@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.username == form_data.username).first()

    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Ungültige Anmeldedaten",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=db_user.username,
        secret=request.app.state.jwt_secret,
        algorithm=settings.jwt_alg,
        expires_minutes=settings.jwt_expire_min,
    )

    return {"access_token": token, "token_type": "bearer"}

@router.get("/auth/check", description="Prüft, ob der aktuelle Token gültig ist.")
def auth_check(user=Depends(get_current_user)):
    return {
        "status": "ok", 
        "user": user['username']
    }

@router.get("/registerCheck", description="Check if a User exist")
def registerCheck(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if user:
        return True
    else:
        return False