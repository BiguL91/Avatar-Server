from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import verify_password, create_access_token, get_current_user

from app.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login mit Email + Passwort, gibt JWT-Token zurueck."""
    from app.services.settings import get_setting
    legacy_login = await get_setting(db, "legacy_login")
    if not legacy_login:
        raise HTTPException(status_code=403, detail="Legacy-Login deaktiviert")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Ungueltige Anmeldedaten")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Ungueltige Anmeldedaten")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deaktiviert")

    token = create_access_token(user.id, user.email, user.is_admin)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
        },
    }


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Aktuellen User zurueckgeben (aus Token oder Dev-Modus)."""
    return user
