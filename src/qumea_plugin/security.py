from datetime import datetime, timedelta, timezone
import os
import secrets
from pathlib import Path
from jose import jwt
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

def get_or_create_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret

    secret_dir = Path("data/secrets")
    secret_file = secret_dir / "jwt_secret"

    secret_dir.mkdir(parents=True, exist_ok=True)

    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()

    secret = secrets.token_urlsafe(64)
    secret_file.write_text(secret, encoding="utf-8")

    try:
        os.chmod(secret_file, 0o600)
    except Exception:
        pass

    return secret
