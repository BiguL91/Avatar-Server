from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Benutzer - lokal angelegt oder via OIDC."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="local")  # "local" oder "oidc"
    oidc_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)  # IdP User-ID (sub-Claim)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Beziehung zu Avataren
    avatars: Mapped[list["Avatar"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Avatar(Base):
    """Avatar-Upload eines Benutzers."""

    __tablename__ = "avatars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    crop_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-String
    original_path: Mapped[str] = mapped_column(Text)  # Pfad zur Original-Datei
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Beziehung zum User
    user: Mapped["User"] = relationship(back_populates="avatars")


class Setting(Base):
    """Einstellungen - ueberschreiben ENV-Defaults zur Laufzeit."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
