from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db import Base


class Account(Base):
    __tablename__ = "accounts"

    profile_id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    verified      = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True), nullable=True)

class Profile(Base):
    __tablename__ = "profiles"
 
    profile_id      = Column(UUID(as_uuid=True), ForeignKey("accounts.profile_id"), primary_key=True)
    display_name    = Column(String, nullable=False)
    major           = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    clubs           = Column(Array(String), nullable=False, server_default="{}")
    varsity_sports  = Column(Array(String), nullable=True)
    bio             = Column(String, nullable=True)
    interests       = Column(Array(String), nullable=False)
    favorite_bar    = Column(String, nullable=True)
    likes_going_out = Column(Boolean, nullable=True)
    smokes          = Column(Boolean, nullable=True)
    nicotine_lover  = Column(Boolean, nullable=True)
    height          = Column(Integer, nullable=True)
    gender          = Column(Enum('woman', 'man', 'nonbinary', 'queer/other', name="self_gender", create_type=False))
    looking_for     = Column(
                        Array(Enum('romantic', 'roommate', name="match_type_enum", create_type=False)),
                        nullable=False,
                        server_default="{}"
                      )
    romantically_searching_for  = Column(
                        Array(Enum('something serious', 'open for anything', 'short-term fun', name="searching_type_enum", create_type=False)),
                        nullable=False,
                        server_default="{}"
                      )
    status          = Column(Enum("active", "suspended", "deleted", name="profile_status", create_type=False), nullable=False, server_default="active")
    last_active     = Column(DateTime(timezone=True), server_default=func.now())
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now())


class ActiveMatch(Base):
    __tablename__ = "active_matches"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id_a = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"), nullable=False)
    profile_id_b = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"), nullable=False)
    match_type   = Column(ENUM("romantic", "friend", "roommate", name="match_type_enum", create_type=False), nullable=False)
    matched_at   = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_match_id = Column(UUID(as_uuid=True), ForeignKey("active_matches.id"), nullable=False, unique=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    sender_id       = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id"), nullable=False)
    content         = Column(String, nullable=False)
    sent_at         = Column(DateTime(timezone=True), server_default=func.now())
    read            = Column(Boolean, nullable=False, default=False)