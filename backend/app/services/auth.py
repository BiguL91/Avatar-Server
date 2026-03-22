from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

# Bearer-Token Schema fuer Swagger-UI
security = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    """Passwort hashen mit bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Passwort gegen Hash pruefen."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, email: str, is_admin: bool) -> str:
    """JWT-Token erstellen mit User-Daten und Ablaufzeit."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """JWT-Token decodieren und Claims zurueckgeben."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungueltiger oder abgelaufener Token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aktuellen User aus JWT-Token ermitteln.

    Dev-Modus: Ohne Token wird der Fake-User zurueckgegeben.
    """
    # Dev-Modus: Fake-User wenn kein Token vorhanden
    if settings.dev_mode and credentials is None:
        # Dev-User in DB sicherstellen
        result = await db.execute(select(User).where(User.email == settings.dev_user_email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=settings.dev_user_email,
                name=settings.dev_user_name,
                source="local",
                is_admin=False,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
        }

    # Token erforderlich
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht angemeldet",
        )

    # Token decodieren
    payload = decode_token(credentials.credentials)

    # User aus DB laden (stellt sicher, dass er noch existiert)
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User nicht gefunden",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deaktiviert",
        )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_admin": user.is_admin,
    }


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """Nur Admins durchlassen - fuer Admin-Endpunkte."""
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur fuer Administratoren",
        )
    return user
