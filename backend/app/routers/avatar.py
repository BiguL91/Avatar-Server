import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
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
async def get_avatar(hash_value: str, s: int | None = None, db: AsyncSession = Depends(get_db)):
    """Avatar ausliefern - erkennt .png Endung automatisch."""
    # .png Endung erkennen und als PNG ausliefern
    if hash_value.endswith(".png"):
        raw_hash = hash_value[:-4]
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
    filepath, cache_max_age = await _resolve_avatar(hash_value, s, db)
    return FileResponse(
        filepath,
        media_type="image/webp",
        headers={"Cache-Control": f"public, max-age={cache_max_age}"},
    )
