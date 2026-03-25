from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Zentrale Konfiguration - wird aus ENV-Variablen geladen."""

    # Allgemein
    app_name: str = "Avatar Server"
    debug: bool = False

    # Avatar-Speicherung
    avatar_storage_path: str = "./data/avatars"
    avatar_default_size: int = 80
    avatar_max_size: int = 512
    avatar_sizes: list[int] = [32, 64, 80, 128, 256, 512]
    avatar_upload_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    avatar_original_max_px: int = 1920  # FullHD laengste Seite
    avatar_cache_max_age: int = 3600  # Cache-Dauer in Sekunden (1 Stunde)
    avatar_max_uploads: int = 6  # Maximale Anzahl gespeicherter Avatare pro User

    # OIDC / SSO
    oidc_enabled: bool = False
    oidc_discovery_url: str = ""  # Basis-URL z.B. https://sso.domain.com/realms/myrealm
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_claim_email: str = "email"
    oidc_claim_name: str = "nickname"
    oidc_claim_picture: str = "picture"
    oidc_claim_picture_png: str = "avatar_png"  # Attribut-Name fuer PNG-Avatar-URL im IdP
    oidc_claim_groups: str = "groups"
    oidc_admin_group: str = "admin"  # Gruppenname der Admin-Rechte vergibt
    oidc_sync_picture: bool = False  # Avatar-URL an IdP zurueckschreiben
    oidc_picture_size: int = 256  # Groesse fuer die Picture-URL
    base_url: str = "http://localhost:8000"

    # Sprache (de, en)
    default_language: str = "de"

    # Datenbank
    database_path: str = "./data/avatar_server.db"

    # Admin-User (wird beim ersten Start angelegt)
    admin_email: str = ""
    admin_password: str = ""

    # JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 1440  # 24 Stunden

    # Legacy-Login (Email + Passwort)
    legacy_login: bool = True

    # Security
    trusted_proxy: str = ""  # IP oder Subnetz z.B. 192.168.1.10 oder 192.168.1.0/24
    allowed_hosts: str = "localhost"  # Komma-separiert z.B. localhost,avatars.domain.de,192.168.1.50

    # Dev-Modus: OIDC umgehen mit Fake-User
    dev_mode: bool = False
    dev_user_email: str = "dev@example.com"
    dev_user_name: str = "Dev User"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
