import hashlib
import json
import shutil
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Avatar, User
from app.services.settings import get_setting


def hash_email(email: str) -> dict[str, str]:
    """E-Mail-Adresse zu MD5 und SHA256 Hash konvertieren."""
    normalized = email.strip().lower()
    return {
        "md5": hashlib.md5(normalized.encode()).hexdigest(),
        "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
    }


def _get_user_dir(email: str) -> Path:
    """User-Verzeichnis anhand des Email-Hashes."""
    hashes = hash_email(email)
    return Path(settings.avatar_storage_path) / "users" / hashes["sha256"]


async def _get_or_create_user(db: AsyncSession, email: str, name: str = "", source: str = "local") -> User:
    """User aus DB holen oder neu anlegen."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user

    # Neuen User anlegen
    user = User(email=email, name=name or email, source=source)
    db.add(user)
    await db.flush()
    return user


def _publish_active(email: str, upload_id: int) -> None:
    """Bilder eines Uploads in die oeffentlichen Hash-Verzeichnisse kopieren."""
    user_dir = _get_user_dir(email)
    upload_dir = user_dir / str(upload_id)
    hashes = hash_email(email)
    storage = Path(settings.avatar_storage_path)

    for hash_type, hash_value in hashes.items():
        hash_dir = storage / hash_type / hash_value
        # Altes Verzeichnis leeren
        if hash_dir.exists():
            shutil.rmtree(hash_dir)
        hash_dir.mkdir(parents=True, exist_ok=True)

        # Bilder kopieren (ohne Original)
        for webp_file in upload_dir.glob("*.webp"):
            if webp_file.name != "original.webp":
                shutil.copy2(webp_file, hash_dir / webp_file.name)


def _normalize_image(image_bytes: bytes) -> Image.Image:
    """Bild laden, EXIF korrigieren, Transparenz beibehalten (RGBA) oder in RGB konvertieren."""
    img = Image.open(BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P", "LA", "PA"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    return img


def _apply_crop(img: Image.Image, crop: dict | None = None) -> Image.Image:
    """Crop anwenden und quadratisch machen."""
    if crop:
        w, h = img.size
        left = int(w * crop["x"] / 100)
        top = int(h * crop["y"] / 100)
        right = left + int(w * crop["width"] / 100)
        bottom = top + int(h * crop["height"] / 100)
        img = img.crop((left, top, right, bottom))

    size = min(img.size)
    img = ImageOps.fit(img, (size, size))
    return img


def _save_sizes(img: Image.Image, upload_dir: Path, sizes: list[int] | None = None) -> None:
    """Bild in allen konfigurierten Groessen speichern."""
    for target_size in (sizes or settings.avatar_sizes):
        resized = img.copy()
        resized = resized.resize((target_size, target_size), Image.LANCZOS)
        filepath = upload_dir / f"{target_size}.webp"
        resized.save(filepath, "WEBP", quality=85)


async def process_and_save(db: AsyncSession, image_bytes: bytes, email: str, name: str, crop: dict | None = None) -> dict:
    """Bild verarbeiten und als neuen Upload speichern.

    Returns:
        Dict mit upload_id, hashes und created_at
    """
    img = _normalize_image(image_bytes)
    cropped = _apply_crop(img.copy(), crop)

    # User in DB sicherstellen
    user = await _get_or_create_user(db, email, name)

    # Upload-Verzeichnis erstellen (ID wird von DB vergeben)
    # Zuerst Avatar-Eintrag anlegen um Auto-Increment ID zu bekommen
    user_dir = _get_user_dir(email)
    crop_json = json.dumps(crop) if crop else None

    avatar = Avatar(
        user_id=user.id,
        is_active=False,
        crop_data=crop_json,
        original_path="",  # Wird nach Verzeichnis-Erstellung gesetzt
    )
    db.add(avatar)
    await db.flush()  # ID wird vergeben

    upload_dir = user_dir / str(avatar.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Original auf max. Aufloesung begrenzen und speichern
    original = img.copy()
    max_px = await get_setting(db, "avatar_original_max_px")
    if original.width > max_px or original.height > max_px:
        original.thumbnail((max_px, max_px), Image.LANCZOS)
    original.save(upload_dir / "original.webp", "WEBP", quality=95)

    # Pfad zum Original in DB speichern
    avatar.original_path = str(upload_dir / "original.webp")

    # Cropped Versionen speichern
    avatar_sizes = await get_setting(db, "avatar_sizes")
    _save_sizes(cropped, upload_dir, avatar_sizes)

    # Pruefen ob User bereits einen aktiven Avatar hat
    active_count = await db.execute(
        select(func.count()).select_from(Avatar).where(Avatar.user_id == user.id, Avatar.is_active == True)
    )
    has_active = active_count.scalar() > 0

    # Erster Upload wird automatisch aktiv
    if not has_active:
        avatar.is_active = True

    await db.commit()

    # Wenn aktiv -> publizieren
    if avatar.is_active:
        _publish_active(email, avatar.id)

    hashes = hash_email(email)
    return {
        "upload_id": avatar.id,
        "hashes": hashes,
        "created_at": avatar.created_at.isoformat(),
        "is_active": avatar.is_active,
    }


async def recrop_upload(db: AsyncSession, email: str, upload_id: int, crop: dict) -> dict:
    """Original-Bild eines Uploads neu croppen und ueberschreiben."""
    user = await _get_or_create_user(db, email)

    # Avatar in DB suchen
    result = await db.execute(
        select(Avatar).where(Avatar.id == upload_id, Avatar.user_id == user.id)
    )
    avatar = result.scalar_one_or_none()
    if not avatar:
        raise ValueError("Upload nicht gefunden")

    user_dir = _get_user_dir(email)
    upload_dir = user_dir / str(upload_id)
    original_path = upload_dir / "original.webp"

    if not original_path.exists():
        raise ValueError("Original-Bild nicht gefunden")

    # Original laden und neu croppen
    img = Image.open(original_path)
    cropped = _apply_crop(img, crop)
    avatar_sizes = await get_setting(db, "avatar_sizes")
    _save_sizes(cropped, upload_dir, avatar_sizes)

    # Crop-Daten in DB aktualisieren
    avatar.crop_data = json.dumps(crop)
    await db.commit()

    # Wenn aktiv -> auch oeffentliche Hashes aktualisieren
    if avatar.is_active:
        _publish_active(email, upload_id)

    hashes = hash_email(email)
    return {
        "upload_id": upload_id,
        "hashes": hashes,
    }


async def activate_upload(db: AsyncSession, email: str, upload_id: int) -> dict:
    """Einen Upload als aktiven Avatar setzen."""
    user = await _get_or_create_user(db, email)

    # Avatar pruefen
    result = await db.execute(
        select(Avatar).where(Avatar.id == upload_id, Avatar.user_id == user.id)
    )
    avatar = result.scalar_one_or_none()
    if not avatar:
        raise ValueError("Upload nicht gefunden")

    # Alle Avatare deaktivieren
    all_avatars = await db.execute(
        select(Avatar).where(Avatar.user_id == user.id)
    )
    for a in all_avatars.scalars():
        a.is_active = False

    # Gewaehlten aktivieren
    avatar.is_active = True
    await db.commit()

    _publish_active(email, upload_id)

    return {"active": upload_id}


async def delete_upload(db: AsyncSession, email: str, upload_id: int) -> dict:
    """Einen Upload loeschen. Aktiver Upload kann nicht geloescht werden."""
    user = await _get_or_create_user(db, email)

    result = await db.execute(
        select(Avatar).where(Avatar.id == upload_id, Avatar.user_id == user.id)
    )
    avatar = result.scalar_one_or_none()
    if not avatar:
        raise ValueError("Upload nicht gefunden")

    if avatar.is_active:
        raise ValueError("Aktiver Avatar kann nicht geloescht werden")

    # Dateien loeschen
    user_dir = _get_user_dir(email)
    upload_dir = user_dir / str(upload_id)
    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    # Aus DB entfernen
    await db.delete(avatar)
    await db.commit()

    return {"deleted": upload_id}


async def delete_all_user_data(db: AsyncSession, email: str) -> dict:
    """Alle Daten eines Users komplett loeschen (Avatare, Metadaten, oeffentliche Hashes)."""
    hashes = hash_email(email)
    storage = Path(settings.avatar_storage_path)

    # User-Verzeichnis loeschen
    user_dir = _get_user_dir(email)
    if user_dir.exists():
        shutil.rmtree(user_dir)

    # Oeffentliche Hash-Verzeichnisse loeschen
    for hash_type, hash_value in hashes.items():
        hash_dir = storage / hash_type / hash_value
        if hash_dir.exists():
            shutil.rmtree(hash_dir)

    # Avatare aus DB loeschen (User bleibt bestehen)
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if user:
        avatars = await db.execute(select(Avatar).where(Avatar.user_id == user.id))
        for avatar in avatars.scalars():
            await db.delete(avatar)
        await db.commit()

    return {"deleted": True}


async def get_history(db: AsyncSession, email: str) -> dict:
    """Alle Uploads eines Users mit Vorschau-URLs zurueckgeben."""
    hashes = hash_email(email)
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()

    if not user:
        return {
            "uploads": [],
            "hashes": hashes,
            "max_uploads": await get_setting(db, "avatar_max_uploads"),
        }

    result = await db.execute(
        select(Avatar).where(Avatar.user_id == user.id).order_by(Avatar.created_at)
    )
    avatars = result.scalars().all()

    uploads = []
    for avatar in avatars:
        uploads.append({
            "id": avatar.id,
            "created_at": avatar.created_at.isoformat(),
            "is_active": avatar.is_active,
            "thumbnail": f"/api/uploads/{hashes['sha256']}/{avatar.id}/64.webp",
        })

    return {
        "uploads": uploads,
        "hashes": hashes,
        "max_uploads": await get_setting(db, "avatar_max_uploads"),
    }


async def get_active_avatar_info(db: AsyncSession, email: str) -> dict:
    """Infos zum aktiven Avatar eines Users (fuer /upload/me)."""
    hashes = hash_email(email)
    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()

    has_avatar = False
    if user:
        result = await db.execute(
            select(Avatar).where(Avatar.user_id == user.id, Avatar.is_active == True)
        )
        has_avatar = result.scalar_one_or_none() is not None

    return {
        "md5": hashes["md5"],
        "has_avatar": has_avatar,
    }
