import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.routers import admin, auth, avatar, oidc, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown-Lifecycle: DB initialisieren, Admin-User anlegen."""
    from app.database import init_db
    await init_db()
    await _seed_admin_user()
    yield


async def _seed_admin_user():
    """Erstellt den Admin-User aus ENV beim ersten Start (falls konfiguriert)."""
    if not settings.admin_email or not settings.admin_password:
        return

    from sqlalchemy import select

    from app.database import async_session
    from app.models import User
    from app.services.auth import hash_password

    async with async_session() as db:
        # Pruefen ob Admin bereits existiert
        result = await db.execute(select(User).where(User.email == settings.admin_email))
        existing = result.scalar_one_or_none()

        if existing:
            return

        # Admin-User anlegen
        admin = User(
            email=settings.admin_email,
            name="Administrator",
            password_hash=hash_password(settings.admin_password),
            source="local",
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print(f"[DB] Admin-User angelegt: {settings.admin_email}")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS fuer Frontend-Zugriff
_cors_origins = ["http://localhost:5173"]
if settings.base_url and settings.base_url != "http://localhost:8000":
    _cors_origins.append(settings.base_url.rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(admin.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(oidc.router, prefix="/api")
app.include_router(avatar.router)
app.include_router(upload.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    """Oeffentliche Konfiguration fuer das Frontend."""
    from app.services.settings import get_setting
    default_language = await get_setting(db, "default_language")
    avatar_sizes = await get_setting(db, "avatar_sizes") or settings.avatar_sizes
    oidc_enabled = await get_setting(db, "oidc_enabled")
    return {
        "defaultLanguage": default_language or "de",
        "devMode": bool(settings.dev_mode),
        "oidcEnabled": bool(oidc_enabled),
        "avatarSizes": sorted(avatar_sizes),
    }


# Statische Frontend-Dateien ausliefern (nur wenn Build vorhanden)
STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.is_dir():
    # Statische Assets (JS, CSS, Bilder)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA-Fallback: Alle unbekannten Routen auf index.html (z.B. /oidc/callback)."""
        file_path = (STATIC_DIR / full_path).resolve()
        # Path-Traversal verhindern
        if full_path and file_path.is_relative_to(STATIC_DIR.resolve()) and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
