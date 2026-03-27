from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from .db.database import get_db

from .config import get_settings
from .security import decode_token

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.token_url)

def get_jwt_secret(request: Request) -> str:
    secret = getattr(request.app.state, "jwt_secret", None)
    if not secret:
        raise RuntimeError("JWT secret not initialized")
    return secret

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    secret: str = Depends(get_jwt_secret),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nicht autorisiert",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token=token, secret=secret, algorithm=settings.jwt_alg)
        username: str | None = payload.get("sub")
        if not username:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception