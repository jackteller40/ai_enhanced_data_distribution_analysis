from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db import Base


class Account(Base):
    __tablename__ = "accounts"

    profile_id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    university    = Column(String, nullable=False)
    verified      = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True), nullable=True)

class Profile(Base):
    __tablename__ = "profiles"
 
    profile_id      = Column(UUID(as_uuid=True), ForeignKey("accounts.profile_id"), primary_key=True)
    display_name    = Column(String, nullable=False)
    major           = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    bio             = Column(String, nullable=True)
    favorite_bar    = Column(String, nullable=True)
    likes_going_out = Column(Boolean, nullable=True)
    smokes          = Column(Boolean, nullable=True)
    clubs           = Column(ARRAY(String), nullable=False, server_default="{}")
    looking_for     = Column(
                        ARRAY(ENUM("romantic", "friend", "roommate", name="match_type_enum", create_type=False)),
                        nullable=False,
                        server_default="{}"
                      )
    status          = Column(ENUM("active", "suspended", "deleted", name="profile_status", create_type=False), nullable=False, server_default="active")
    last_active     = Column(DateTime(timezone=True), server_default=func.now())
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now())