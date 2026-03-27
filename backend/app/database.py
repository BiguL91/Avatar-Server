from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# SQLite-Datenbank im data-Verzeichnis (gleicher Ordner wie Avatare)
# Pfad wird absolut aufgeloest, damit SQLite die Datei immer findet
db_path = Path(settings.database_path).resolve()
db_path.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI-Dependency: liefert eine DB-Session pro Request."""
    async with async_session() as session:
        yield session


async def init_db():
    """Erstellt alle Tabellen beim Start (falls nicht vorhanden) und fuehrt Migrationen durch."""
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Migration: is_active Spalte zu users hinzufuegen (falls nicht vorhanden)
        def _migrate_is_active(connection):
            from sqlalchemy import text, inspect
            inspector = inspect(connection)
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "is_active" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))

        await conn.run_sync(_migrate_is_active)

        # Migration: oidc_sub Spalte zu users hinzufuegen (IdP User-ID)
        def _migrate_oidc_sub(connection):
            from sqlalchemy import text, inspect
            inspector = inspect(connection)
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "oidc_sub" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN oidc_sub VARCHAR(255)"))

        await conn.run_sync(_migrate_oidc_sub)

        # Migration: is_locked Spalte zu avatars hinzufuegen (Avatar sperren)
        def _migrate_is_locked(connection):
            from sqlalchemy import text, inspect
            inspector = inspect(connection)
            columns = [col["name"] for col in inspector.get_columns("avatars")]
            if "is_locked" not in columns:
                connection.execute(text("ALTER TABLE avatars ADD COLUMN is_locked BOOLEAN DEFAULT 0 NOT NULL"))

        await conn.run_sync(_migrate_is_locked)

        # Migration: avatar_public Spalte zu users hinzufuegen (Avatar Access Control)
        def _migrate_avatar_public(connection):
            from sqlalchemy import text, inspect
            inspector = inspect(connection)
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "avatar_public" not in columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN avatar_public BOOLEAN DEFAULT 0 NOT NULL"))

        await conn.run_sync(_migrate_avatar_public)
