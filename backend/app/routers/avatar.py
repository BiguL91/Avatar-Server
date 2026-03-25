import hashlib
import io
import ipaddress
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.settings import get_setting

router = APIRouter()


def detect_hash_type(hash_str: str) -> str:
    """Hash-Typ anhand der Laenge erkennen (32 = MD5, 64 = SHA256)."""
    import re

    if not re.fullmatch(r"[a-fA-F0-9]+", hash_str):
        raise HTTPException(status_code=400, detail="Ungueltiger Hash (nur Hex-Zeichen erlaubt)")
    if len(hash_str) == 32:
        return "md5"
    elif len(hash_str) == 64:
        return "sha256"
    raise HTTPException(status_code=400, detail="Ungueltiger Hash (muss 32 oder 64 Zeichen lang sein)")


async def _find_user_by_hash(hash_str: str, hash_type: str, db: AsyncSession) -> User | None:
    """User anhand des Email-Hashes finden."""
    result = await db.execute(select(User))
    for user in result.scalars().all():
        email_normalized = user.email.strip().lower()
        if hash_type == "md5":
            computed = hashlib.md5(email_normalized.encode()).hexdigest()
        else:
            computed = hashlib.sha256(email_normalized.encode()).hexdigest()
        if computed == hash_str.lower():
            return user
    return None


async def _check_avatar_access(request: Request, hash_str: str, hash_type: str, db: AsyncSession) -> None:
    """Prueft ob der Avatar-Zugriff erlaubt ist (Access Control)."""
    avatar_access = await get_setting(db, "avatar_access") or "public"

    # Public-Modus: alle Avatare frei erreichbar
    if avatar_access != "subnet":
        return

    # Eingeloggte User duerfen Avatare immer sehen (Subnet gilt nur fuer anonyme Zugriffe)
    from app.services.auth import decode_token

    # Token aus Authorization-Header (Frontend laedt Avatare per fetch mit Auth-Header)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token_data = decode_token(auth_header.split(" ", 1)[1])
        if token_data:
            return

    # Subnet-Modus: User mit avatar_public=True sind frei erreichbar
    user = await _find_user_by_hash(hash_str, hash_type, db)
    if user and user.avatar_public:
        return

    # Subnet-Pruefung
    client_ip = request.client.host if request.client else None
    if not client_ip:
        raise HTTPException(status_code=403, detail="Avatar-Zugriff gesperrt")

    allowed_subnets = await get_setting(db, "avatar_allowed_subnets") or ""
    if not allowed_subnets.strip():
        # Keine Subnets konfiguriert aber Modus ist subnet = alles blockiert
        raise HTTPException(status_code=403, detail="Avatar-Zugriff gesperrt (keine Subnetze konfiguriert)")

    # Pruefen ob Client-IP in einem erlaubten Subnet liegt
    subnets = [s.strip() for s in allowed_subnets.split(",") if s.strip()]
    for subnet in subnets:
        try:
            if ipaddress.ip_address(client_ip) in ipaddress.ip_network(subnet, strict=False):
                return
        except ValueError:
            continue

    raise HTTPException(status_code=403, detail="Avatar-Zugriff nur aus erlaubten Subnetzen moeglich")


async def _resolve_avatar(hash_str: str, s: int | None, db: AsyncSession) -> tuple[Path, int]:
    """Avatar-Dateipfad und Cache-Dauer ermitteln."""
    hash_type = detect_hash_type(hash_str)

    if s is None:
        s = await get_setting(db, "avatar_default_size") or 80

    available = sorted(await get_setting(db, "avatar_sizes") or settings.avatar_sizes)
    target_size = available[-1]
    for size in available:
        if size >= s:
            target_size = size
            break

    filepath = Path(settings.avatar_storage_path) / hash_type / hash_str / f"{target_size}.webp"

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Avatar nicht gefunden")

    cache_max_age = await get_setting(db, "avatar_cache_max_age")
    return filepath, cache_max_age


@router.get("/avatar/{hash_value}")
async def get_avatar(hash_value: str, s: int | None = None, request: Request = None, db: AsyncSession = Depends(get_db)):
    """Avatar ausliefern - erkennt .png Endung automatisch."""
    # .png Endung erkennen und als PNG ausliefern
    if hash_value.endswith(".png"):
        raw_hash = hash_value[:-4]
        hash_type = detect_hash_type(raw_hash)
        await _check_avatar_access(request, raw_hash, hash_type, db)
        filepath, cache_max_age = await _resolve_avatar(raw_hash, s, db)

        img = Image.open(filepath)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": f"public, max-age={cache_max_age}"},
        )

    # Standard: WebP ausliefern
    hash_type = detect_hash_type(hash_value)
    await _check_avatar_access(request, hash_value, hash_type, db)
    filepath, cache_max_age = await _resolve_avatar(hash_value, s, db)
    return FileResponse(
        filepath,
        media_type="image/webp",
        headers={"Cache-Control": f"public, max-age={cache_max_age}"},
    )
