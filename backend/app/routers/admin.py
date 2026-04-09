from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User, UserRole
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


class UserAdminResponse(UserPublic):
    is_active: bool


class RoleUpdateRequest:
    pass


@router.get("/users", response_model=dict)
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar()

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "role": u.role.value,
                "storage_used": u.storage_used,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.patch("/users/{user_id}/role", response_model=UserPublic)
async def update_user_role(
    user_id: UUID,
    payload: dict,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    role_value = payload.get("role")
    if role_value not in ("viewer", "uploader", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(role_value)
    await db.commit()
    await db.refresh(user)
    return user
