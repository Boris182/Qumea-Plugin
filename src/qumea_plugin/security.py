from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt

def crypt_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(*, subject: str, secret: str, algorithm: str, expires_minutes: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, secret, algorithm=algorithm)

def decode_token(*, token: str, secret: str, algorithm: str) -> dict:
    # wirft JWTError wenn ungültig
    return jwt.decode(token, secret, algorithms=[algorithm])
