import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from sqlalchemy import select

from app.database import get_db
from app.services.auth import get_current_user
from app.services.image import (
    process_and_save,
    activate_upload,
    delete_upload,
    delete_all_user_data,
    get_history,
    get_active_avatar_info,
    recrop_upload,
)
from app.services.oidc import sync_picture_to_idp
from app.config import settings
from app.models import User
from app.services.settings import get_setting

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sync_picture_if_state_changed(db: AsyncSession, user_email: str, had_avatar_before: bool):
    """Avatar-URL an den IdP synchronisieren wenn sich der Zustand aendert.

    Wird nur ausgefuehrt wenn sich der Status von "kein Avatar" zu "hat Avatar"
    oder umgekehrt aendert. Der Hash basiert auf der Email und bleibt immer gleich.
    """
    sync_enabled = await get_setting(db, "oidc_sync_picture")
    if not sync_enabled:
        return

    # Aktuellen Zustand pruefen
    avatar_info = await get_active_avatar_info(db, user_email)
    has_avatar_now = bool(avatar_info.get("has_avatar"))

    # Nur synchronisieren wenn sich der Zustand geaendert hat
    if has_avatar_now == had_avatar_before:
        return

    # oidc_sub aus der DB holen (nur OIDC-User haben eine IdP-ID)
    result = await db.execute(select(User).where(User.email == user_email))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.oidc_sub:
        return

    discovery_url = await get_setting(db, "oidc_discovery_url")
    client_id = await get_setting(db, "oidc_client_id")
    client_secret = await get_setting(db, "oidc_client_secret")
    if not all([discovery_url, client_id, client_secret]):
        return

    base_url = (await get_setting(db, "base_url") or "http://localhost:8000").rstrip("/")
    picture_size = await get_setting(db, "oidc_picture_size") or 256
    claim_name = await get_setting(db, "oidc_claim_picture") or "picture"
    claim_name_png = await get_setting(db, "oidc_claim_picture_png") or "avatar_png"

    if has_avatar_now and avatar_info.get("md5"):
        md5 = avatar_info["md5"]
        picture_url = f"{base_url}/avatar/{md5}?s={picture_size}"
        picture_png_url = f"{base_url}/avatar/{md5}.png?s={picture_size}"
    else:
        picture_url = None
        picture_png_url = None

    await sync_picture_to_idp(
        discovery_url=discovery_url,
        client_id=client_id,
        client_secret=client_secret,
        oidc_sub=db_user.oidc_sub,
        picture_url=picture_url,
        picture_png_url=picture_png_url,
        claim_name=claim_name,
        claim_name_png=claim_name_png,
    )


@router.get("/upload/me")
async def get_me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Aktuellen User zurueckgeben (inkl. Avatar-Status)."""
    avatar_info = await get_active_avatar_info(db, user["email"])
    return {
        **user,
        **avatar_info,
    }


@router.post("/upload")
async def upload_avatar(
    file: UploadFile = File(...),
    crop_x: float = Form(0),
    crop_y: float = Form(0),
    crop_width: float = Form(100),
    crop_height: float = Form(100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Avatar hochladen, croppen und in allen Groessen speichern."""
    image_bytes = await file.read()

    # Dateigroesse pruefen
    max_bytes = await get_setting(db, "avatar_upload_max_bytes")
    if len(image_bytes) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"Datei zu gross (max. {max_mb} MB)")

    # Upload-Limit pruefen
    max_uploads = await get_setting(db, "avatar_max_uploads")
    history = await get_history(db, user["email"])
    if len(history["uploads"]) >= max_uploads:
        raise HTTPException(status_code=400, detail=f"Maximum {max_uploads} Avatare erreicht")

    # Vorher-Zustand merken (fuer Picture-Sync)
    avatar_before = await get_active_avatar_info(db, user["email"])
    had_avatar = bool(avatar_before.get("has_avatar"))

    crop = {
        "x": crop_x,
        "y": crop_y,
        "width": crop_width,
        "height": crop_height,
    }

    result = await process_and_save(db, image_bytes, user["email"], user["name"], crop)

    # Avatar-URL an IdP synchronisieren (nur bei Zustandsaenderung)
    await _sync_picture_if_state_changed(db, user["email"], had_avatar)

    return {
        "success": True,
        **result,
    }


@router.get("/history")
async def get_upload_history(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Alle Uploads des Users zurueckgeben."""
    return await get_history(db, user["email"])


@router.post("/activate/{upload_id}")
async def set_active(upload_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Einen Upload als aktiven Avatar setzen."""
    try:
        result = await activate_upload(db, user["email"], upload_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.delete("/uploads/{upload_id}")
async def remove_upload(upload_id: int, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Einen Upload loeschen."""
    try:
        result = await delete_upload(db, user["email"], upload_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/uploads/{user_hash}/{upload_id}/{filename}")
async def get_upload_image(user_hash: str, upload_id: int, filename: str):
    """Bild eines bestimmten Uploads ausliefern (fuer Thumbnails)."""
    import re

    # Path-Traversal verhindern: nur sichere Zeichen erlauben
    if not re.fullmatch(r"[a-fA-F0-9]{32,64}", user_hash):
        raise HTTPException(status_code=400, detail="Ungueltiger Hash")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", filename):
        raise HTTPException(status_code=400, detail="Ungueltiger Dateiname")

    base_dir = Path(settings.avatar_storage_path).resolve() / "users"
    filepath = (base_dir / user_hash / str(upload_id) / filename).resolve()

    # Sicherstellen dass der Pfad innerhalb des erlaubten Verzeichnisses bleibt
    if not filepath.is_relative_to(base_dir):
        raise HTTPException(status_code=400, detail="Ungueltiger Pfad")

    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Bild nicht gefunden")

    return FileResponse(
        filepath,
        media_type="image/webp",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/recrop/{upload_id}")
async def recrop(
    upload_id: int,
    crop_x: float = Form(0),
    crop_y: float = Form(0),
    crop_width: float = Form(100),
    crop_height: float = Form(100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Original-Bild eines Uploads neu croppen."""
    crop = {
        "x": crop_x,
        "y": crop_y,
        "width": crop_width,
        "height": crop_height,
    }
    try:
        result = await recrop_upload(db, user["email"], upload_id, crop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.delete("/account")
async def delete_account_data(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Alle Daten des Users loeschen (Avatare, Metadaten, Hashes)."""
    # Vorher-Zustand merken
    avatar_before = await get_active_avatar_info(db, user["email"])
    had_avatar = bool(avatar_before.get("has_avatar"))

    result = await delete_all_user_data(db, user["email"])

    # Picture-Attribut im IdP entfernen (nur wenn vorher Avatar vorhanden)
    await _sync_picture_if_state_changed(db, user["email"], had_avatar)

    return result


def _is_safe_url(url: str) -> bool:
    """Pruefen ob die URL sicher ist (kein SSRF auf interne Dienste)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # Nur HTTP(S) erlauben
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # DNS aufloesen und alle IPs pruefen
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        return False

    for _, _, _, _, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False

    return True


@router.get("/fetch-image")
async def fetch_image(url: str, _user: dict = Depends(get_current_user)):
    """Bild von externer URL laden und als Proxy zurueckgeben."""
    if not _is_safe_url(url):
        raise HTTPException(status_code=400, detail="URL nicht erlaubt")

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
            response = await client.get(url)
    except httpx.RequestError:
        raise HTTPException(status_code=400, detail="URL nicht erreichbar")

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="URL liefert kein Bild")

    # Maximale Groesse begrenzen (10 MB)
    if len(response.content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu gross")

    return Response(content=response.content, media_type=content_type)
