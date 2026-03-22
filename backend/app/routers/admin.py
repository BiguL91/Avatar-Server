from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Avatar, User
from app.services.auth import get_admin_user, hash_password
from app.services.settings import (
    CONFIGURABLE_KEYS,
    delete_setting,
    get_all_settings,
    set_setting,
)

router = APIRouter()


# === User-Verwaltung ===


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str


class UpdateUserRequest(BaseModel):
    name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = None


@router.get("/admin/users")
async def list_users(
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alle User mit Avatar-Anzahl auflisten."""
    # User + Avatar-Count per Subquery
    avatar_count = (
        select(Avatar.user_id, func.count(Avatar.id).label("count"))
        .group_by(Avatar.user_id)
        .subquery()
    )

    result = await db.execute(
        select(User, avatar_count.c.count)
        .outerjoin(avatar_count, User.id == avatar_count.c.user_id)
        .order_by(User.created_at)
    )

    users = []
    for user, count in result.all():
        users.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "source": user.source,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "avatar_count": count or 0,
            "created_at": user.created_at.isoformat(),
        })

    return {"users": users}


@router.post("/admin/users")
async def create_user(
    body: CreateUserRequest,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Lokalen User anlegen."""
    # Pruefen ob Email bereits vergeben
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-Mail bereits vergeben")

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
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
        "source": user.source,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


@router.patch("/admin/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """User bearbeiten (Email, Name, Admin-Status, Aktiv-Status, Passwort)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    if body.name is not None:
        user.name = body.name
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.is_active is not None:
        # Eigenen Account nicht deaktivieren
        if user.id == admin["id"] and not body.is_active:
            raise HTTPException(status_code=400, detail="Eigenen Account kann man nicht deaktivieren")
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    await db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """User und alle seine Daten loeschen."""
    from app.services.image import delete_all_user_data

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    # Eigenen Account nicht loeschen
    if user.id == admin["id"]:
        raise HTTPException(status_code=400, detail="Eigenen Account kann man nicht loeschen")

    # Avatar-Dateien loeschen
    await delete_all_user_data(db, user.email)

    # User aus DB loeschen (Avatare werden per CASCADE mitgeloescht)
    await db.delete(user)
    await db.commit()

    return {"deleted": user_id}


# === Settings-Verwaltung ===


class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/admin/settings")
async def list_settings(
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alle konfigurierbaren Settings auflisten."""
    return {"settings": await get_all_settings(db)}


@router.put("/admin/settings/{key}")
async def update_setting(
    key: str,
    body: UpdateSettingRequest,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Setting in DB speichern (ueberschreibt ENV-Default)."""
    if key not in CONFIGURABLE_KEYS:
        raise HTTPException(status_code=400, detail=f"Setting '{key}' ist nicht konfigurierbar")

    from app.services.settings import get_setting

    # OIDC aktivieren: HTTPS, Trusted Proxy und kein Dev-Mode
    if key == "oidc_enabled" and body.value.lower() in ("true", "1", "yes"):
        dev_mode = await get_setting(db, "dev_mode")
        if dev_mode:
            raise HTTPException(
                status_code=400,
                detail="OIDC kann nicht aktiviert werden solange Dev-Mode aktiv ist.",
            )

        base_url = await get_setting(db, "base_url") or ""
        if not base_url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="OIDC erfordert HTTPS. Bitte zuerst BASE_URL auf HTTPS setzen.",
            )

        trusted_proxy = await get_setting(db, "trusted_proxy")
        if not trusted_proxy:
            raise HTTPException(
                status_code=400,
                detail="OIDC erfordert einen TRUSTED_PROXY. Bitte zuerst Trusted Proxy konfigurieren.",
            )

        discovery_url = await get_setting(db, "oidc_discovery_url") or ""
        if discovery_url and not discovery_url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="OIDC_DISCOVERY_URL muss HTTPS sein.",
            )

    # Discovery-URL aendern: muss HTTPS sein
    if key == "oidc_discovery_url" and body.value.strip() and not body.value.strip().startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="OIDC_DISCOVERY_URL muss HTTPS sein.",
        )

    # Dev-Mode aktivieren: nicht wenn OIDC aktiv
    if key == "dev_mode" and body.value.lower() in ("true", "1", "yes"):
        oidc_enabled = await get_setting(db, "oidc_enabled")
        if oidc_enabled:
            raise HTTPException(
                status_code=400,
                detail="Dev-Mode kann nicht aktiviert werden solange OIDC aktiv ist.",
            )

    # BASE_URL aendern: wenn OIDC aktiv, muss HTTPS bleiben
    if key == "base_url":
        oidc_enabled = await get_setting(db, "oidc_enabled")
        if oidc_enabled and not body.value.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="BASE_URL muss HTTPS sein solange OIDC aktiviert ist.",
            )

    # Trusted Proxy aendern: wenn OIDC aktiv, darf nicht leer sein
    if key == "trusted_proxy" and not body.value.strip():
        oidc_enabled = await get_setting(db, "oidc_enabled")
        if oidc_enabled:
            raise HTTPException(
                status_code=400,
                detail="TRUSTED_PROXY darf nicht leer sein solange OIDC aktiviert ist.",
            )

    setting = await set_setting(db, key, body.value)
    return {
        "key": setting.key,
        "value": setting.value,
        "source": "db",
    }


@router.delete("/admin/settings/{key}")
async def reset_setting(
    key: str,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """DB-Override loeschen (zurueck auf ENV-Default)."""
    if key not in CONFIGURABLE_KEYS:
        raise HTTPException(status_code=400, detail=f"Setting '{key}' ist nicht konfigurierbar")

    # Pruefen ob Reset sicher ist wenn OIDC aktiv
    from app.config import settings as env_settings
    from app.services.settings import get_setting

    oidc_enabled = await get_setting(db, "oidc_enabled")
    if oidc_enabled:
        if key == "trusted_proxy" and not env_settings.trusted_proxy:
            raise HTTPException(
                status_code=400,
                detail="TRUSTED_PROXY kann nicht zurueckgesetzt werden solange OIDC aktiviert ist (kein ENV-Default vorhanden).",
            )
        if key == "base_url" and not env_settings.base_url.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="BASE_URL kann nicht zurueckgesetzt werden solange OIDC aktiviert ist (ENV-Default ist nicht HTTPS).",
            )

    deleted = await delete_setting(db, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kein DB-Override vorhanden")

    return {"reset": key}
