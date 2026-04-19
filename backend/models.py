from sqlalchemy import Column, String, Boolean, Integer, ARRAY, Enum, ForeignKey, DateTime, func, Text, Float, Date, CheckConstraint, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, CITEXT, JSONB
import uuid
from db import Base


class Account(Base):
    __tablename__ = "accounts"

    profile_id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(CITEXT, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        CheckConstraint("email ~ '^[^@\\s]+@marist\\.edu$'", name="accounts_email_domain"),
    )

class Profile(Base):
    __tablename__ = "profiles"
 
    profile_id = Column(UUID(as_uuid=True), ForeignKey("accounts.profile_id", ondelete="CASCADE"), primary_key=True)
    display_name    = Column(String, nullable=False)
    major           = Column(String, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    clubs           = Column(ARRAY(String), nullable=False, server_default="{}")
    varsity_sports  = Column(ARRAY(String), nullable=True)
    bio             = Column(String, nullable=True)
    interests       = Column(ARRAY(String), nullable=True)
    favorite_bar    = Column(String, nullable=True)
    likes_going_out = Column(Boolean, nullable=True)
    smokes          = Column(Boolean, nullable=True)
    nicotine_lover  = Column(Boolean, nullable=True)
    height          = Column(Integer, nullable=True)
    gender          = Column(Enum('woman', 'man', 'nonbinary', 'queer/other', name="self_gender", create_type=False))
    looking_for     = Column(
                        ARRAY(Enum('romantic', 'roommate', name="match_type_enum", create_type=False)),
                        nullable=False,
                        server_default="{}"
                      )
    romantically_searching_for  = Column(
                        Enum('something serious', 'open for anything', 'short-term fun', name="relationship_type_enum", create_type=False),
                        nullable=True
                      )
    status          = Column(Enum("active", "suspended", "deleted", name="profile_status", create_type=False), nullable=False, server_default="active")
    last_active     = Column(DateTime(timezone=True), server_default=func.now())
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("length(trim(display_name)) > 1", name="profiles_display_name_not_empty"),
        CheckConstraint("graduation_year IS NULL OR graduation_year BETWEEN 1960 AND 2035", name="profiles_grad_year_sane"),
    )

class ActiveMatch(Base):
    __tablename__ = "active_matches"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id_a = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="RESTRICT"), nullable=False)
    profile_id_b = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="RESTRICT"), nullable=False)
    match_type   = Column(Enum("romantic", "roommate", name="match_type_enum", create_type=False), nullable=False)
    matched_at   = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("profile_id_a < profile_id_b", name="active_matches_ordered"),
        UniqueConstraint("profile_id_a", "profile_id_b", "match_type"),
    )
    

class Conversation(Base):
    __tablename__ = "conversations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_match_id = Column(UUID(as_uuid=True), ForeignKey("active_matches.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id       = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    recipient_id    = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    content         = Column(String, nullable=False)
    sent_at         = Column(DateTime(timezone=True), server_default=func.now())
    read            = Column(Boolean, nullable=False, default=False)
    __table_args__ = (
        CheckConstraint("length(trim(content)) > 0", name="messages_content_not_empty"),
        CheckConstraint("length(content) <= 4000", name="messages_content_length"),
    )
class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id  = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    photo_base64 = Column(Text, nullable=False)
    position    = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("position >= 0", name="profile_photos_position_nonneg"),
        UniqueConstraint("profile_id", "position"),
    )


class RomanticPreference(Base):
    __tablename__ = "romantic_preferences"

    profile_id           = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), primary_key=True)
    interested_in_genders = Column(
                              ARRAY(Enum('women', 'men', 'nonbinary/queer identities', 'everyone', name="gender_preference", create_type=False)),
                              nullable=True
                            )
    own_gender           = Column(Enum('woman', 'man', 'nonbinary', 'queer/other', name="self_gender", create_type=False), nullable=True)
    min_grad_yr          = Column(Integer, nullable=True)
    max_grad_yr          = Column(Integer, nullable=True)
    relationship_style   = Column(Enum('something serious', 'open for anything', 'short-term fun', name="relationship_type_enum", create_type=False), nullable=True)
    priority_weights     = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at           = Column(DateTime(timezone=True), server_default=func.now())


class RoommatePreference(Base):
    __tablename__ = "roommate_preferences"

    profile_id                = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), primary_key=True)
    roommate_gender_preference = Column(Enum('women', 'men', 'nonbinary/queer identities', 'everyone', name="gender_preference", create_type=False), nullable=True)
    sleep_schedule            = Column(Enum('early bird', 'night owl', 'flexible', name="sleep_schedule_enum", create_type=False), nullable=True)
    cleanliness               = Column(Integer, nullable=True)
    noise_tolerance           = Column(Integer, nullable=True)
    has_pets                  = Column(Boolean, nullable=True)
    ok_with_pets              = Column(Boolean, nullable=True)
    guests_frequency          = Column(Enum('often', 'rarely', 'sometimes', name="guests_frequency_enum", create_type=False), nullable=True)
    on_campus                 = Column(Boolean, nullable=True)
    priority_weights          = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    updated_at                = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("cleanliness IS NULL OR cleanliness BETWEEN 1 AND 5", name="roommate_cleanliness_range"),
        CheckConstraint("noise_tolerance IS NULL OR noise_tolerance BETWEEN 1 AND 5", name="roommate_noise_range"),
    )


class Suggestion(Base):
    __tablename__ = "suggestions"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receiver_id      = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    candidate_id     = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    match_type       = Column(Enum("romantic", "roommate", name="match_type_enum", create_type=False), nullable=False)
    status           = Column(Enum("pending", "liked", "rejected", "matched", name="suggestion_status", create_type=False), nullable=False, server_default="pending")
    match_score      = Column(Float, nullable=True)
    agent_explanation = Column(Text, nullable=True)
    suggested_date   = Column(Date, nullable=False, server_default=func.current_date())
    acted_at         = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("receiver_id <> candidate_id", name="suggestions_no_self_match"),
        UniqueConstraint("receiver_id", "candidate_id", "match_type"),
    )


class RejectedMatch(Base):
    __tablename__ = "rejected_matches"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rejecter_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    rejected_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), nullable=False)
    match_type  = Column(Enum("romantic", "roommate", name="match_type_enum", create_type=False), nullable=False)
    rejected_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("rejecter_id <> rejected_id", name="rejected_no_self"),
        UniqueConstraint("rejecter_id", "rejected_id", "match_type"),
    )

class Report(Base):
    __tablename__ = "reports"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="SET NULL"), nullable=True)
    reported_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="RESTRICT"), nullable=False)
    reason      = Column(Enum("harassment", "inappropriate_content", "fake_profile", "spam", "safety_concern", "other", name="report_reason", create_type=False), nullable=False)
    details     = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Text, nullable=True)
    resolution  = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("details IS NULL OR length(details) <= 2000", name="reports_details_length"),
        CheckConstraint("reporter_id IS NULL OR reporter_id <> reported_id", name="reports_no_self"),
    )


class BlockedUser(Base):
    __tablename__ = "blocked_users"

    blocker_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), primary_key=True)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("profiles.profile_id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    report_id  = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("blocker_id <> blocked_id", name="blocked_no_self"),
    )