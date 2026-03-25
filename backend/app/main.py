import ipaddress
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import get_db
from app.routers import admin, auth, avatar, oidc, upload


def _check_security():
    """Sicherheitspruefungen beim Start."""
    is_https = settings.base_url.startswith("https://")

    if settings.oidc_enabled and settings.dev_mode:
        print("[SECURITY] OIDC und Dev-Mode sind gleichzeitig aktiviert!")
        print("[SECURITY] Dev-Mode umgeht die Authentifizierung — das ist mit OIDC nicht sicher.")
        print("[SECURITY] Bitte DEV_MODE=false setzen oder OIDC deaktivieren.")
        sys.exit(1)

    if settings.oidc_enabled and not is_https:
        print("[SECURITY] OIDC ist aktiviert aber BASE_URL ist nicht HTTPS!")
        print(f"[SECURITY] BASE_URL: {settings.base_url}")
        print("[SECURITY] OIDC-Tokens werden unverschluesselt uebertragen.")
        print("[SECURITY] Server wird nicht gestartet. Bitte BASE_URL auf HTTPS setzen")
        print("[SECURITY] oder einen Reverse-Proxy mit SSL-Terminierung verwenden.")
        sys.exit(1)

    if settings.oidc_enabled and settings.oidc_discovery_url and not settings.oidc_discovery_url.startswith("https://"):
        print("[SECURITY] OIDC_DISCOVERY_URL ist nicht HTTPS!")
        print(f"[SECURITY] OIDC_DISCOVERY_URL: {settings.oidc_discovery_url}")
        print("[SECURITY] Die Kommunikation mit dem IdP muss verschluesselt sein.")
        sys.exit(1)

    if settings.oidc_enabled and not settings.trusted_proxy:
        print("[SECURITY] OIDC ist aktiviert aber kein TRUSTED_PROXY gesetzt!")
        print("[SECURITY] Ohne Trusted Proxy kann der Server direkt umgangen werden.")
        print("[SECURITY] Bitte TRUSTED_PROXY auf die IP/Subnetz des Reverse-Proxy setzen.")
        sys.exit(1)

    if not is_https and not settings.dev_mode:
        print("[SECURITY] HINWEIS: BASE_URL ist nicht HTTPS. Fuer Produktion HTTPS verwenden.")

    if settings.jwt_secret == "dev-secret-change-me" and not settings.dev_mode:
        print("[SECURITY] WARNUNG: JWT_SECRET ist auf dem Default-Wert! Bitte aendern.")

    if settings.trusted_proxy:
        print(f"[SECURITY] Trusted Proxy: {settings.trusted_proxy}")

    if settings.allowed_hosts and settings.allowed_hosts != "localhost":
        print(f"[SECURITY] Allowed Hosts: {settings.allowed_hosts}")
    elif settings.allowed_hosts == "localhost":
        print("[SECURITY] Allowed Hosts: localhost (Standard — nur lokaler Zugriff)")


class AllowedHostsMiddleware(BaseHTTPMiddleware):
    """Prueft den Host-Header gegen die erlaubten Hosts (ENV + DB-Override).
    Blockiert Requests mit nicht erlaubtem Host-Header."""

    async def dispatch(self, request: Request, call_next):
        from app.database import async_session
        from app.services.settings import get_setting

        async with async_session() as db:
            allowed_hosts = await get_setting(db, "allowed_hosts")

        # Kein Wert = alle Hosts erlaubt
        if not allowed_hosts or not allowed_hosts.strip():
            return await call_next(request)

        # Host-Header extrahieren (ohne Port)
        host_header = request.headers.get("host", "")
        request_host = host_header.split(":")[0].strip().lower()

        # Erlaubte Hosts parsen
        allowed = [h.strip().lower() for h in allowed_hosts.split(",") if h.strip()]

        if request_host not in allowed:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Zugriff ueber '{host_header}' nicht erlaubt. "
                    f"Erlaubte Hosts: {', '.join(allowed)}"
                },
            )

        return await call_next(request)


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """Prueft Trusted Proxy dynamisch (ENV + DB-Override).
    Wenn der Request vom Trusted Proxy kommt, wird die echte Client-IP
    aus dem X-Forwarded-For Header uebernommen."""

    async def dispatch(self, request: Request, call_next):
        # Trusted Proxy dynamisch aus DB/ENV laden
        from app.database import async_session
        from app.services.settings import get_setting

        async with async_session() as db:
            trusted_proxy = await get_setting(db, "trusted_proxy")

        # Kein Proxy konfiguriert = kein Filter
        if not trusted_proxy:
            return await call_next(request)

        trusted_network = ipaddress.ip_network(trusted_proxy, strict=False)
        client_ip = request.client.host if request.client else None

        if client_ip:
            try:
                if ipaddress.ip_address(client_ip) not in trusted_network:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Zugriff nur ueber Trusted Proxy erlaubt"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Ungueltige Client-IP"},
                )

        # Echte Client-IP aus X-Forwarded-For uebernehmen
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            real_ip = forwarded_for.split(",")[0].strip()
            request.scope["client"] = (real_ip, request.client.port if request.client else 0)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown-Lifecycle: DB initialisieren, Admin-User anlegen."""
    from app.database import init_db
    _check_security()
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
    version="0.1.4",
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

# Trusted Proxy Middleware (prueft dynamisch ob konfiguriert)
app.add_middleware(TrustedProxyMiddleware)

# Allowed Hosts Middleware (prueft Host-Header gegen Whitelist)
app.add_middleware(AllowedHostsMiddleware)

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
    app_name = await get_setting(db, "app_name")
    default_language = await get_setting(db, "default_language")
    avatar_sizes = await get_setting(db, "avatar_sizes") or settings.avatar_sizes
    oidc_enabled = await get_setting(db, "oidc_enabled")
    legacy_login = await get_setting(db, "legacy_login")
    dev_mode = await get_setting(db, "dev_mode")
    avatar_access = await get_setting(db, "avatar_access") or "public"
    avatar_user_can_publish = await get_setting(db, "avatar_user_can_publish")
    return {
        "appName": app_name or settings.app_name,
        "defaultLanguage": default_language or "de",
        "devMode": bool(dev_mode),
        "oidcEnabled": bool(oidc_enabled),
        "legacyLogin": legacy_login if legacy_login is not None else True,
        "avatarSizes": sorted(avatar_sizes),
        "avatarAccess": avatar_access,
        "avatarUserCanPublish": bool(avatar_user_can_publish),
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
