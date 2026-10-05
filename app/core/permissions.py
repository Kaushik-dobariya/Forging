from typing import Iterable, Callable
from fastapi import HTTPException, status
from app.models.user import User, UserRole


def is_superadmin(user: User) -> bool:
    """Returns True if the user is a super admin."""
    return user.is_superuser or user.role == UserRole.SUPER_ADMIN.value


def is_admin(user: User) -> bool:
    """Returns True if the user is at least an admin or super admin."""
    return user.is_active and (is_superadmin(user) or user.role == UserRole.ADMIN.value)


def has_role(user: User, allowed_roles: Iterable[str]) -> bool:
    """Checks whether the user holds one of the specified roles."""
    if not user.is_active:
        return False
    if is_superadmin(user):
        return True
    return user.role in allowed_roles


def check_permission(user: User, allowed_roles: Iterable[str]) -> None:
    """Raises HTTPException 403 if the user does not possess required role."""
    if not has_role(user, allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
