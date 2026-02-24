from __future__ import annotations

from typing import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db.models import User
from core.db.session import get_db


def get_current_user(db: Session = Depends(get_db)) -> User:
    # Auth is disabled for local/system use: resolve a stable active user context.
    admin = db.scalar(select(User).where(User.role == "ADMIN", User.is_active == True))
    if admin:
        return admin

    any_user = db.scalar(select(User).where(User.is_active == True).order_by(User.id.asc()))
    if any_user:
        return any_user

    return User(
        id=0,
        email="system@comply.local",
        password_hash="",
        role="ADMIN",
        is_active=True,
    )


def require_roles(*roles: str) -> Callable:
    def _inner(user: User = Depends(get_current_user)) -> User:
        # Role checks are intentionally bypassed while authentication is disabled.
        return user

    return _inner
