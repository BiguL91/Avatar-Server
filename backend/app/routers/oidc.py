"""OIDC-Router fuer SSO-Authentifizierung.

Stellt Endpoints fuer den Authorization Code Flow bereit:
- /auth/oidc/authorize  -> Redirect-URL zum IdP
- /auth/oidc/callback   -> Code gegen Token tauschen, User anlegen/einloggen
- /auth/oidc/logout      -> Logout-URL vom IdP
"""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import create_access_token
from app.services.oidc import (
    build_auth_url,
    build_end_session_url,
    create_state_token,
    decode_id_token,
    exchange_code,
    extract_user_claims,
    fetch_discovery,
    verify_state_token,
)
from app.services.settings import get_setting
from app.models import User

router = APIRouter()


async def _get_oidc_config(db: AsyncSession) -> dict:
    """OIDC-Konfiguration aus Settings laden und pruefen."""
    enabled = await get_setting(db, "oidc_enabled")
    if not enabled:
        raise HTTPException(status_code=404, detail="OIDC ist nicht aktiviert")

    discovery_url = await get_setting(db, "oidc_discovery_url")
    client_id = await get_setting(db, "oidc_client_id")
    client_secret = await get_setting(db, "oidc_client_secret")

    if not all([discovery_url, client_id, client_secret]):
        raise HTTPException(
            status_code=500,
            detail="OIDC-Konfiguration unvollstaendig (Discovery-URL, Client-ID oder Secret fehlt)",
        )

    return {
        "discovery_url": discovery_url,
        "client_id": client_id,
        "client_secret": client_secret,
    }


async def _get_claim_config(db: AsyncSession) -> dict:
    """Konfigurierbare Claim-Namen aus Settings laden."""
    return {
        "email": await get_setting(db, "oidc_claim_email") or "email",
        "name": await get_setting(db, "oidc_claim_name") or "nickname",
        "picture": await get_setting(db, "oidc_claim_picture") or "picture",
        "groups": await get_setting(db, "oidc_claim_groups") or "groups",
    }


@router.get("/auth/oidc/authorize")
async def oidc_authorize(db: AsyncSession = Depends(get_db)):
    """Authorization-URL fuer den OIDC-Provider generieren.

    Das Frontend leitet den User zu dieser URL weiter.
    """
    config = await _get_oidc_config(db)
    discovery = await fetch_discovery(config["discovery_url"])

    # Kryptografische Zufallswerte fuer CSRF- und Replay-Schutz
    nonce = secrets.token_urlsafe(32)
    state = create_state_token(nonce)

    # Redirect-URI: Frontend-Route die den Code empfaengt
    base_url = await get_setting(db, "base_url") or "http://localhost:5173"
    redirect_uri = base_url.rstrip("/") + "/oidc/callback"

    auth_url = build_auth_url(
        discovery=discovery,
        client_id=config["client_id"],
        redirect_uri=redirect_uri,
        state=state,
        nonce=nonce,
    )

    return {"auth_url": auth_url, "state": state}


class OidcCallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/auth/oidc/callback")
async def oidc_callback(body: OidcCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Authorization-Code gegen Token tauschen und User einloggen.

    Erstellt den User automatisch wenn er noch nicht existiert (Auto-Provisioning).
    """
    # State verifizieren (CSRF-Schutz)
    try:
        verify_state_token(body.state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungueltiger State-Parameter")

    config = await _get_oidc_config(db)
    discovery = await fetch_discovery(config["discovery_url"])

    # Redirect-URI muss mit dem authorize-Request uebereinstimmen
    base_url = await get_setting(db, "base_url") or "http://localhost:5173"
    redirect_uri = base_url.rstrip("/") + "/oidc/callback"

    # Code gegen Tokens tauschen
    logger.info(f"[OIDC] Token-Exchange mit redirect_uri={redirect_uri}")
    try:
        token_response = await exchange_code(
            discovery=discovery,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            code=body.code,
            redirect_uri=redirect_uri,
        )
    except Exception as e:
        logger.error(f"[OIDC] Token-Austausch fehlgeschlagen: {e}")
        raise HTTPException(status_code=400, detail=f"Token-Austausch fehlgeschlagen: {e}")

    id_token_raw = token_response.get("id_token")
    access_token = token_response.get("access_token")
    if not id_token_raw:
        logger.error(f"[OIDC] Kein ID-Token erhalten. Response: {token_response}")
        raise HTTPException(status_code=400, detail="Kein ID-Token vom Provider erhalten")

    # ID-Token validieren und Claims extrahieren
    try:
        claims = await decode_id_token(id_token_raw, discovery, config["client_id"], access_token)
    except Exception as e:
        logger.error(f"[OIDC] ID-Token Validierung fehlgeschlagen: {e}")
        raise HTTPException(status_code=400, detail=f"ID-Token Validierung fehlgeschlagen: {e}")

    # User-Daten aus Claims extrahieren
    claim_config = await _get_claim_config(db)
    try:
        user_claims = extract_user_claims(claims, claim_config)
    except ValueError as e:
        logger.error(f"[OIDC] Claims-Extraktion fehlgeschlagen: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Admin-Gruppe pruefen
    admin_group = await get_setting(db, "oidc_admin_group") or "admin"
    is_admin_via_oidc = admin_group in user_claims["groups"]

    # IdP User-ID (sub-Claim) fuer Admin API
    oidc_sub = claims.get("sub")

    # User in DB suchen oder anlegen
    result = await db.execute(select(User).where(User.email == user_claims["email"]))
    user = result.scalar_one_or_none()

    if user:
        # Existierenden User aktualisieren (Name und sub aus OIDC uebernehmen)
        if user.source == "oidc":
            user.name = user_claims["name"]
            user.is_admin = is_admin_via_oidc
        # Bei lokalem User: Admin-Status nur setzen, nicht entziehen
        elif is_admin_via_oidc:
            user.is_admin = True
        # sub immer aktualisieren (fuer Picture-Sync)
        if oidc_sub:
            user.oidc_sub = oidc_sub
    else:
        # Neuen OIDC-User anlegen
        user = User(
            email=user_claims["email"],
            name=user_claims["name"],
            source="oidc",
            is_admin=is_admin_via_oidc,
            is_active=True,
            oidc_sub=oidc_sub,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Pruefen ob Account aktiv ist
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deaktiviert")

    # Eigenes JWT erstellen (wie beim lokalen Login)
    token = create_access_token(user.id, user.email, user.is_admin)

    return {
        "token": token,
        "id_token": id_token_raw,  # Fuer Logout benoetigt
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
        },
    }


class OidcLogoutRequest(BaseModel):
    id_token_hint: str | None = None


@router.post("/auth/oidc/logout")
async def oidc_logout(body: OidcLogoutRequest, db: AsyncSession = Depends(get_db)):
    """Logout-URL vom OIDC-Provider zurueckgeben.

    Nutzt den end_session_endpoint aus dem Discovery-Dokument.
    """
    config = await _get_oidc_config(db)
    discovery = await fetch_discovery(config["discovery_url"])

    base_url = await get_setting(db, "base_url") or "http://localhost:5173"

    logout_url = build_end_session_url(
        discovery=discovery,
        id_token_hint=body.id_token_hint,
        post_logout_redirect_uri=base_url,
    )

    if not logout_url:
        raise HTTPException(
            status_code=404,
            detail="OIDC-Provider unterstuetzt keinen Logout-Endpoint",
        )

    return {"logout_url": logout_url}
