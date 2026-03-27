"""Admin-Endpoints fuer Avatar-Verwaltung (Sperren/Entsperren)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Avatar, User
from app.services.auth import get_admin_user
from app.services.image import hash_email, lock_avatar, unlock_avatar

router = APIRouter()


@router.get("/admin/avatars")
async def list_all_avatars(
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Alle Avatare aller User auflisten (fuer Admin-Tab 'User Avatare')."""
    result = await db.execute(
        select(Avatar, User)
        .join(User, Avatar.user_id == User.id)
        .order_by(User.name, Avatar.created_at)
    )

    avatars = []
    for avatar, user in result.all():
        hashes = hash_email(user.email)
        avatars.append({
            "id": avatar.id,
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "is_active": avatar.is_active,
            "is_locked": avatar.is_locked,
            "created_at": avatar.created_at.isoformat(),
            "thumbnail": f"/api/uploads/{hashes['sha256']}/{avatar.id}/64.webp",
        })

    return {"avatars": avatars}


@router.patch("/admin/avatars/{avatar_id}/lock")
async def toggle_lock(
    avatar_id: int,
    admin: dict = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Avatar sperren oder entsperren."""
    result = await db.execute(select(Avatar).where(Avatar.id == avatar_id))
    avatar = result.scalar_one_or_none()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar nicht gefunden")

    if avatar.is_locked:
        return await unlock_avatar(db, avatar_id)
    else:
        return await lock_avatar(db, avatar_id)
