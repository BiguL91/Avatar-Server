"""OIDC-Service fuer SSO-Authentifizierung.

Unterstuetzt jeden OIDC-kompatiblen Provider (Keycloak, Authentik, Authelia, etc.)
ueber den Standard Discovery-Mechanismus.
"""

import logging
import time
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt

from app.config import settings

logger = logging.getLogger(__name__)

# Cache fuer Discovery-Dokument, JWKS und Service-Account-Token
_discovery_cache: dict = {}
_discovery_cache_time: float = 0
_jwks_cache: dict = {}
_jwks_cache_time: float = 0
_sa_token_cache: str = ""
_sa_token_cache_time: float = 0
CACHE_TTL = 300  # 5 Minuten


async def fetch_discovery(discovery_url: str) -> dict:
    """OIDC Discovery-Dokument laden (mit Cache).

    Haengt automatisch /.well-known/openid-configuration an die Basis-URL an.
    """
    global _discovery_cache, _discovery_cache_time

    now = time.time()
    if _discovery_cache and (now - _discovery_cache_time) < CACHE_TTL:
        return _discovery_cache

    url = discovery_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _discovery_cache = resp.json()
        _discovery_cache_time = now
        return _discovery_cache


async def fetch_jwks(jwks_uri: str) -> dict:
    """JWKS (JSON Web Key Set) vom Provider laden (mit Cache)."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache and (now - _jwks_cache_time) < CACHE_TTL:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
        return _jwks_cache


def build_auth_url(
    discovery: dict,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
) -> str:
    """Authorization-URL fuer den OIDC-Provider zusammenbauen."""
    auth_endpoint = discovery["authorization_endpoint"]
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
    }
    return f"{auth_endpoint}?{urlencode(params)}"


async def exchange_code(
    discovery: dict,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    """Authorization-Code gegen Tokens eintauschen."""
    token_endpoint = discovery["token_endpoint"]
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_endpoint, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()


async def decode_id_token(
    id_token: str, discovery: dict, client_id: str, access_token: str | None = None
) -> dict:
    """ID-Token validieren und Claims extrahieren.

    Nutzt JWKS vom Provider fuer die Signatur-Validierung.
    access_token wird fuer at_hash-Validierung benoetigt (Keycloak sendet diesen Claim).
    """
    jwks_uri = discovery["jwks_uri"]
    jwks = await fetch_jwks(jwks_uri)

    # Header auslesen um den richtigen Key zu finden
    header = jose_jwt.get_unverified_header(id_token)
    kid = header.get("kid")

    # Passenden Key aus JWKS suchen
    rsa_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            rsa_key = key
            break

    if not rsa_key:
        raise ValueError("Kein passender JWKS-Key fuer das ID-Token gefunden")

    # Token decodieren und validieren
    claims = jose_jwt.decode(
        id_token,
        rsa_key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=discovery.get("issuer"),
        access_token=access_token,
    )
    return claims


def extract_user_claims(claims: dict, claim_config: dict) -> dict:
    """Relevante User-Daten aus den ID-Token Claims extrahieren.

    claim_config enthaelt die konfigurierbaren Claim-Namen:
    {
        "email": "email",
        "name": "nickname",
        "picture": "picture",
        "groups": "groups",
    }
    """
    email = claims.get(claim_config["email"])
    if not email:
        raise ValueError(f"Pflicht-Claim '{claim_config['email']}' fehlt im ID-Token")

    name = claims.get(claim_config["name"]) or email.split("@")[0]
    picture = claims.get(claim_config["picture"])
    groups = claims.get(claim_config["groups"], [])

    # Groups kann ein String oder eine Liste sein
    if isinstance(groups, str):
        groups = [groups]

    return {
        "email": email.lower().strip(),
        "name": name,
        "picture": picture,
        "groups": groups,
    }


def build_end_session_url(
    discovery: dict,
    id_token_hint: str | None = None,
    post_logout_redirect_uri: str | None = None,
) -> str | None:
    """Logout-URL aus dem Discovery-Dokument zusammenbauen."""
    end_session_endpoint = discovery.get("end_session_endpoint")
    if not end_session_endpoint:
        return None

    params = {}
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    if post_logout_redirect_uri:
        params["post_logout_redirect_uri"] = post_logout_redirect_uri

    if params:
        return f"{end_session_endpoint}?{urlencode(params)}"
    return end_session_endpoint


def create_state_token(nonce: str) -> str:
    """Signierten State-Token erstellen (CSRF-Schutz).

    Nutzt das bestehende JWT-Secret um einen kurzlebigen Token zu erzeugen.
    """
    import time
    payload = {
        "nonce": nonce,
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,  # 10 Minuten gueltig
        "purpose": "oidc_state",
    }
    return jose_jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_state_token(state: str) -> dict:
    """State-Token verifizieren und Claims zurueckgeben."""
    try:
        return jose_jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        raise ValueError("Ungueltiger oder abgelaufener State-Token")


# --- Keycloak Admin API: Picture-Attribut synchronisieren ---


async def _get_service_account_token(token_endpoint: str, client_id: str, client_secret: str) -> str:
    """Service-Account-Token via Client Credentials Grant holen (mit Cache)."""
    global _sa_token_cache, _sa_token_cache_time

    now = time.time()
    if _sa_token_cache and (now - _sa_token_cache_time) < CACHE_TTL:
        return _sa_token_cache

    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_endpoint, data=data, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
        _sa_token_cache = token_data["access_token"]
        _sa_token_cache_time = now
        return _sa_token_cache


async def sync_picture_to_idp(
    discovery_url: str,
    client_id: str,
    client_secret: str,
    oidc_sub: str,
    picture_url: str | None,
    picture_png_url: str | None,
    claim_name: str = "picture",
    claim_name_png: str = "avatar_png",
) -> bool:
    """Avatar-URLs als Attribute im IdP setzen.

    Nutzt die Keycloak Admin API ueber einen Service Account:
    1. Token via Client Credentials holen
    2. User direkt per sub (IdP User-ID) ansprechen
    3. picture + picture_png Attribute aktualisieren

    Gibt True zurueck bei Erfolg, False bei Fehler.
    """
    try:
        # Admin-API Basis-URL aus der Discovery-URL ableiten
        # z.B. https://sso.domain.com/realms/myrealm -> https://sso.domain.com/admin/realms/myrealm
        base = discovery_url.rstrip("/")
        parts = base.split("/realms/")
        if len(parts) != 2:
            logger.error("[OIDC] Discovery-URL hat kein /realms/ - Admin API nicht ableitbar")
            return False

        admin_base = f"{parts[0]}/admin/realms/{parts[1]}"

        # Discovery fuer Token-Endpoint
        discovery = await fetch_discovery(discovery_url)
        token_endpoint = discovery["token_endpoint"]

        # Service-Account-Token holen
        sa_token = await _get_service_account_token(token_endpoint, client_id, client_secret)

        async with httpx.AsyncClient() as client:
            # User direkt per ID laden
            resp = await client.get(
                f"{admin_base}/users/{oidc_sub}",
                headers={"Authorization": f"Bearer {sa_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            idp_user = resp.json()

            # Nur die Attribute im kompletten User-Objekt aendern
            attributes = idp_user.get("attributes", {})
            if picture_url:
                attributes[claim_name] = [picture_url]
                attributes[claim_name_png] = [picture_png_url] if picture_png_url else []
            else:
                # Kein Avatar -> Attribute entfernen
                attributes.pop(claim_name, None)
                attributes.pop(claim_name_png, None)

            idp_user["attributes"] = attributes

            resp = await client.put(
                f"{admin_base}/users/{oidc_sub}",
                json=idp_user,
                headers={"Authorization": f"Bearer {sa_token}"},
                timeout=10,
            )
            resp.raise_for_status()

            logger.info(f"[OIDC] Picture-Attribut fuer {oidc_sub} aktualisiert: {picture_url}")
            return True

    except Exception as e:
        logger.error(f"[OIDC] Picture-Sync fehlgeschlagen fuer {oidc_sub}: {e}")
        return False
