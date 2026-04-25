from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(unique=True)
    found_at: Mapped[datetime] = mapped_column(server_default=func.now())

    created_at: Mapped[datetime] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str]
    followers: Mapped[int]
    following: Mapped[int]
    posts: Mapped[int]
    verified: Mapped[bool]