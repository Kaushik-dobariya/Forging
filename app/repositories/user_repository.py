from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


class UserRepository:
    """Repository handling all database persistence operations for User entity."""

    def get_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.scalar(select(User).where(User.id == user_id))

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        clean_email = email.strip().lower()
        return db.scalar(select(User).where(func.lower(User.email) == clean_email))

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return list(db.scalars(select(User).offset(skip).limit(limit)).all())

    def count_superadmins(self, db: Session) -> int:
        return db.scalar(
            select(func.count(User.id)).where(
                (User.role == UserRole.SUPER_ADMIN.value) | (User.is_superuser == True)
            )
        ) or 0

    def create(
        self,
        db: Session,
        user_in: UserCreate,
        hashed_password: str,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=user_in.email.strip().lower(),
            hashed_password=hashed_password,
            full_name=user_in.full_name.strip(),
            role=user_in.role.value if hasattr(user_in.role, "value") else str(user_in.role),
            is_active=user_in.is_active,
            is_superuser=is_superuser,
            failed_login_attempts=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def record_failed_attempt(
        self,
        db: Session,
        user: User,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
    ) -> User:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= max_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def reset_failed_attempts(self, db: Session, user: User) -> User:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_profile(
        self,
        db: Session,
        user: User,
        full_name: str,
        email: str,
    ) -> User:
        """Updates administrator profile information (full_name and email)."""
        user.full_name = full_name.strip()
        user.email = email.strip().lower()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_password(
        self,
        db: Session,
        user: User,
        hashed_password: str,
    ) -> User:
        """Updates administrator hashed password and clears failed attempts."""
        user.hashed_password = hashed_password
        user.failed_login_attempts = 0
        user.locked_until = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


user_repository = UserRepository()
