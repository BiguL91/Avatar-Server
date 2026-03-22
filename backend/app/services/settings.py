import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as env_settings
from app.models import Setting

# Settings die zur Laufzeit ueber die Admin-Konsole aenderbar sind
CONFIGURABLE_KEYS = {
    "avatar_max_uploads": "int",
    "avatar_cache_max_age": "int",
    "default_language": "str",
    "avatar_upload_max_bytes": "int",
    "avatar_original_max_px": "int",
    "avatar_default_size": "int",
    "avatar_max_size": "int",
    "avatar_sizes": "list",
    # Login / Security
    "legacy_login": "bool",
    "trusted_proxy": "str",
    "base_url": "str",
    "dev_mode": "bool",
    # OIDC / SSO
    "oidc_enabled": "bool",
    "oidc_discovery_url": "str",
    "oidc_client_id": "str",
    "oidc_client_secret": "str",
    "oidc_claim_email": "str",
    "oidc_claim_name": "str",
    "oidc_claim_picture": "str",
    "oidc_claim_picture_png": "str",
    "oidc_claim_groups": "str",
    "oidc_admin_group": "str",
    "oidc_sync_picture": "bool",
    "oidc_picture_size": "int",
}


async def get_setting(db: AsyncSession, key: str) -> str | int | None:
    """Setting aus DB laden, Fallback auf ENV-Default."""
    # Zuerst DB pruefen
    result = await db.execute(select(Setting).where(Setting.key == key))
    db_setting = result.scalar_one_or_none()

    if db_setting is not None:
        value = db_setting.value
    else:
        # Fallback auf ENV/Pydantic-Settings
        value = getattr(env_settings, key, None)
        if value is None:
            return None
        value = str(value)

    # Typ-Konvertierung
    setting_type = CONFIGURABLE_KEYS.get(key, "str")
    if setting_type == "int":
        return int(value)
    if setting_type == "bool":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    if setting_type == "list":
        if isinstance(value, list):
            return value
        return json.loads(value)
    return value


async def set_setting(db: AsyncSession, key: str, value: str) -> Setting:
    """Setting in DB speichern (Upsert)."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = Setting(key=key, value=value)
        db.add(existing)

    await db.commit()
    return existing


async def delete_setting(db: AsyncSession, key: str) -> bool:
    """DB-Override loeschen (zurueck auf ENV-Default)."""
    result = await db.execute(select(Setting).where(Setting.key == key))
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return True
    return False


# Keys deren Werte in der Admin-Konsole maskiert werden
SECRET_KEYS = {"oidc_client_secret"}


async def get_all_settings(db: AsyncSession) -> list[dict]:
    """Alle konfigurierbaren Settings mit Quelle (env/db) zurueckgeben."""
    # Alle DB-Overrides laden
    result = await db.execute(select(Setting))
    db_settings = {s.key: s for s in result.scalars().all()}

    settings_list = []
    for key, value_type in CONFIGURABLE_KEYS.items():
        env_value = getattr(env_settings, key, None)
        db_setting = db_settings.get(key)

        if db_setting:
            display_value = db_setting.value
        elif isinstance(env_value, list):
            display_value = json.dumps(env_value)
        else:
            display_value = str(env_value)

        # Secrets maskieren (nur letzte 4 Zeichen zeigen)
        if key in SECRET_KEYS and display_value and len(display_value) > 4:
            display_value = "****" + display_value[-4:]

        settings_list.append({
            "key": key,
            "value": display_value,
            "source": "db" if db_setting else "env",
            "type": value_type,
            "updated_at": db_setting.updated_at.isoformat() if db_setting else None,
        })

    return settings_list
