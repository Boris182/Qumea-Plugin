from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from ..db.models import User
from ..security import decode_token


def get_user_from_token(
    *,
    raw_token: str,
    db: Session,
    secret: str,
    algorithm: str,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültiger oder fehlender Token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token=raw_token, secret=secret, algorithm=algorithm)
        username: str | None = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.user_name == user_name).first()
    if not user:
        raise credentials_exception

    return user


def require_role(user: User, *allowed_roles: str) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Berechtigung",
        )