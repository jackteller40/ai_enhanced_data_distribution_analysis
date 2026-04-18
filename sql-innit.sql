-- ============================================================================
-- University matching app — complete Postgres schema (v1)
--
-- Usage:
--   createdb matchapp
--   psql matchapp -f schema.sql
--
-- This script is written to be re-runnable on a FRESH database. It is NOT
-- safe to run against an existing database with data — use Alembic migrations
-- for that. For the pilot, dropping and recreating is fine.
--
-- Decisions locked in this file (search for DECISION: to find them):
--   - profiles.looking_for is an array of match_type
--   - ON DELETE CASCADE on most child rows; RESTRICT on active_matches
--   - Preference tables have concrete v1 columns alongside priority_weights JSONB
--   - Photos split into a separate table (multiple per profile, ordered)
--   - last_active on profiles for match-pool freshness
--   - reports and profile_status for the safety/moderation story
--   - Two DB roles: app_user (read/write) and matcher_ro (read-only)
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Extensions
-- ----------------------------------------------------------------------------

-- gen_random_uuid() for primary keys. Built into Postgres 13+.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- citext for case-insensitive email comparison without .lower() everywhere.
CREATE EXTENSION IF NOT EXISTS citext;


-- ----------------------------------------------------------------------------
-- Enums
-- ----------------------------------------------------------------------------

CREATE TYPE match_type_enum AS ENUM ('romantic', 'roommate');
CREATE TYPE searching_type_enum AS ENUM ('something serious', 'open for anything', 'short-term fun');
CREATE TYPE self_gender AS ENUM ('woman', 'man', 'nonbinary', 'queer/other');
CREATE TYPE gender_preference AS ENUM ('women', 'men', 'nonbinary/queer identities', 'everyone');
CREATE TYPE sleep_schedule_enum AS ENUM ('early bird', 'night owl', 'flexible');
CREATE TYPE guests_frequency_enum AS ENUM ('often', 'rarely', 'sometimes');

-- Suggestion lifecycle. See project_context.md for the full state machine.
-- pending  -> no one has acted
-- liked    -> receiver accepted; waiting on candidate
-- matched  -> both accepted; active_matches row exists
-- rejected -> terminal, but in practice we DELETE the row and write to
--             rejected_matches instead. Kept in the enum for completeness
--             and in case we ever want to keep rejection history on the
--             suggestion itself.
CREATE TYPE suggestion_status AS ENUM ('pending', 'liked', 'rejected', 'matched');

-- Soft-disable without delete. Suspended profiles disappear from matching
-- but their conversation history stays intact for the people they matched with.
CREATE TYPE profile_status AS ENUM ('active', 'suspended', 'deleted');

-- Report categories. Kept short on purpose — too many buckets = worse signal
-- for moderators. Tune after seeing real reports.
CREATE TYPE report_reason AS ENUM (
    'harassment',
    'inappropriate_content',
    'fake_profile',
    'spam',
    'safety_concern',
    'other'
);


-- ----------------------------------------------------------------------------
-- accounts
--
-- Auth-only data. Separated from profiles so auth can be managed independently
-- (rotating password hashes, adding OAuth, etc.) without touching profile schema.
-- Shared PK with profiles enforces the 1-to-1 at the database level.
-- ----------------------------------------------------------------------------

CREATE TABLE accounts (
    profile_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login      TIMESTAMPTZ,

    -- Basic email check that it ends with @marist.edu
    CONSTRAINT accounts_email_domain CHECK (email ~ '^[^@\s]+@marist\.edu$')
);

-- ----------------------------------------------------------------------------
-- profiles
--
-- User-facing data. 1-to-1 with accounts via shared profile_id.
-- DECISION: looking_for is match_type_enum[], not a single value. Users
-- commonly want more than one type (e.g. roommate AND friend).
-- ----------------------------------------------------------------------------

CREATE TABLE profiles (
    profile_id       UUID PRIMARY KEY REFERENCES accounts(profile_id) ON DELETE CASCADE,
    display_name     TEXT NOT NULL,
    major            TEXT,
    graduation_year  INT,
    clubs            TEXT[] NOT NULL DEFAULT '{}',
    varsity_sports   TEXT[],
    bio              TEXT,
    interests        TEXT[],
    favorite_bar     TEXT,
    likes_going_out  BOOLEAN,
    smokes           BOOLEAN,
    nicotine_lover   BOOLEAN,
    height          INT, --people can input as 5 foot 2, then a helper function will convert to inches that it is stored by
    gender          self_gender,

    -- Which match types the user is currently open to. Empty array = matching paused.
    looking_for      match_type_enum[] NOT NULL DEFAULT '{}',
    romantically_searching_for    searching_type_enum,

    -- Status controls whether the profile appears in matching and whether
    -- the account can log in. See profile_status enum above.
    status           profile_status NOT NULL DEFAULT 'active',

    -- Used by the nightly matcher to skip stale users. Updated on login and
    -- on any meaningful app activity (viewing suggestions, swiping, messaging).
    last_active      TIMESTAMPTZ NOT NULL DEFAULT now(),

    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT profiles_grad_year_sane
        CHECK (graduation_year IS NULL OR graduation_year BETWEEN 1960 AND 2035),
    CONSTRAINT profiles_display_name_not_empty
        CHECK (length(trim(display_name)) > 1)
);

-- Matcher filters heavily on status and last_active. This index makes the
-- "pool of matchable users" query cheap even as the table grows.
CREATE INDEX profiles_active_idx ON profiles (status, last_active DESC)
    WHERE status = 'active';

-- GIN index on looking_for so we can cheaply answer "users open to roommate matching".
CREATE INDEX profiles_looking_for_idx ON profiles USING GIN (looking_for);

-- GIN index on looking_for so we can cheaply answer "users open to something serious".
CREATE INDEX profiles_romantically_searching_for_idx ON profiles (romantically_searching_for);

-- GIN index on clubs for the scoring function's club-overlap computation.
CREATE INDEX profiles_clubs_idx ON profiles USING GIN (clubs);


-- ----------------------------------------------------------------------------
-- profile_photos
--
-- Multiple photos per profile, ordered. Stores basep4 photo urls. 
-- ----------------------------------------------------------------------------

CREATE TABLE profile_photos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id  UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    photo_base64  TEXT NOT NULL,          -- base64 link to the photo
    position    INT NOT NULL,           -- 0-indexed order; 0 is primary photo
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT profile_photos_position_nonneg CHECK (position >= 0),
    UNIQUE (profile_id, position)
);

CREATE INDEX profile_photos_profile_idx ON profile_photos (profile_id, position);


-- ----------------------------------------------------------------------------
-- Preference tables — three separate tables, one per match type.
--
-- DECISION: The fields differ meaningfully between use cases, so flattening
-- these into one table would create a sparse mess. Each table has its own
-- concrete columns PLUS a priority_weights JSONB blob. The scoring function
-- reads both: concrete columns provide the *values* to match against,
-- priority_weights provides the *weights* to apply.
--
-- priority_weights shape: {"field_name": 0.0..1.0, ...}
-- Example for romantic: {"major": 0.3, "clubs": 0.5, "smoking": 1.0,
--                        "gender": 1.0, "going_out": 0.6}
--
-- All weights are optional; missing keys are treated as 0 (don't care).
-- ----------------------------------------------------------------------------

CREATE TABLE romantic_preferences (
    profile_id          UUID PRIMARY KEY REFERENCES profiles(profile_id) ON DELETE CASCADE,

    -- Who they're interested in
    interested_in_genders gender_preference[],  -- e.g. {'woman', 'nonbinary'}

    -- Self-reported; used by OTHER people's romantic_preferences for matching.
    -- Stored here rather than profiles because it's only meaningful for romantic matching.
    own_gender          self_gender,

    -- Age range they're open to. NULL = no preference on that bound.
    min_grad_yr             INT,
    max_grad_yr             INT,

    -- Relationship style they're seeking. 
    -- once we see what values people actually use.
    relationship_style  searching_type_enum,  

    priority_weights    JSONB NOT NULL DEFAULT '{}'::jsonb,

    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT romantic_weights_is_object
        CHECK (jsonb_typeof(priority_weights) = 'object')
);

CREATE TABLE roommate_preferences (
    profile_id          UUID PRIMARY KEY REFERENCES profiles(profile_id) ON DELETE CASCADE,
    roommate_gender_preference   gender_preference,

    -- The fields that actually matter for living together.
    -- These are the v1 guess — tune after seeing pilot data.
    sleep_schedule      sleep_schedule_enum,  -- "early_bird", "night_owl", "flexible"
    cleanliness         INT,   -- 1-5 self-rating
    noise_tolerance     INT,   -- 1-5 (1 = need silence, 5 = party-fine)
    has_pets            BOOLEAN,
    ok_with_pets        BOOLEAN,
    guests_frequency    guests_frequency_enum,  -- "rarely", "sometimes", "often"
    on_campus          BOOLEAN,

    priority_weights    JSONB NOT NULL DEFAULT '{}'::jsonb,

    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT roommate_cleanliness_range
        CHECK (cleanliness IS NULL OR cleanliness BETWEEN 1 AND 5),
    CONSTRAINT roommate_noise_range
        CHECK (noise_tolerance IS NULL OR noise_tolerance BETWEEN 1 AND 5),
    CONSTRAINT roommate_weights_is_object
        CHECK (jsonb_typeof(priority_weights) = 'object')
);

-- ----------------------------------------------------------------------------
-- suggestions
--
-- The swipe queue. Agent writes here nightly. DIRECTIONAL — one row per
-- (receiver, candidate, match_type). When receiver likes, row stays but
-- status flips so it appears in candidate's queue too (the query filters
-- by either status='pending' for me as receiver, or status='liked' where
-- I am the candidate).
-- ----------------------------------------------------------------------------

CREATE TABLE suggestions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    receiver_id        UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    candidate_id       UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    match_type         match_type_enum NOT NULL,
    status             suggestion_status NOT NULL DEFAULT 'pending',
    match_score        FLOAT,
    agent_explanation  TEXT,
    suggested_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    acted_at           TIMESTAMPTZ,

    CONSTRAINT suggestions_no_self_match CHECK (receiver_id <> candidate_id),
    UNIQUE (receiver_id, candidate_id, match_type)
);

-- Primary query: "give me user X's pending queue for match_type T, ordered by score"
CREATE INDEX suggestions_receiver_queue_idx
    ON suggestions (receiver_id, match_type, status, match_score DESC);

-- Inbound-likes lookup: "who has liked me that I haven't seen yet?"
-- The nightly matcher uses this to boost candidates who already liked the receiver.
CREATE INDEX suggestions_inbound_likes_idx
    ON suggestions (candidate_id, match_type, status)
    WHERE status = 'liked';


-- ----------------------------------------------------------------------------
-- rejected_matches
--
-- Permanent rejection log. Matcher filters this before generating suggestions
-- so rejected profiles never resurface. Two rows per rejection (one per
-- direction) so neither party sees the other again regardless of who rejected.
-- ----------------------------------------------------------------------------

CREATE TABLE rejected_matches (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rejecter_id    UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    rejected_id   UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    match_type    match_type_enum NOT NULL,
    rejected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT rejected_no_self CHECK (rejecter_id <> rejected_id),
    UNIQUE (rejecter_id, rejected_id, match_type)
);

-- Matcher's anti-join against this table runs per-user, per-match-type.
CREATE INDEX rejected_matches_profile_type_idx
    ON rejected_matches (rejecter_id, match_type);


-- ----------------------------------------------------------------------------
-- active_matches
--
-- Created when both users accept each other. Unlocks conversation.
-- DECISION: profile_id_a < profile_id_b (by UUID string) is enforced by CHECK
-- so the UNIQUE constraint actually prevents dupes. Two users CAN be active
-- matches across multiple types simultaneously — match_type is part of the key.
-- ----------------------------------------------------------------------------

CREATE TABLE active_matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id_a    UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE RESTRICT,
    profile_id_b    UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE RESTRICT,
    match_type      match_type_enum NOT NULL,
    matched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- The ordering constraint is what makes the UNIQUE below actually unique.
    -- App code must always sort the two UUIDs before INSERT.
    CONSTRAINT active_matches_ordered CHECK (profile_id_a < profile_id_b),
    UNIQUE (profile_id_a, profile_id_b, match_type)
);

CREATE INDEX active_matches_a_idx ON active_matches (profile_id_a, match_type);
CREATE INDEX active_matches_b_idx ON active_matches (profile_id_b, match_type);


-- ----------------------------------------------------------------------------
-- conversations
--
-- One per active_match. Container for messages. Deleting the active_match
-- cascades to conversation and its messages — intentional: if users "unmatch",
-- the history goes with it.
-- ----------------------------------------------------------------------------

CREATE TABLE conversations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    active_match_id  UUID NOT NULL UNIQUE
                     REFERENCES active_matches(id) ON DELETE CASCADE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- messages
--
-- One row per message. Never a packed blob.
-- ----------------------------------------------------------------------------

CREATE TABLE messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id        UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    recipient_id     UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    content          TEXT NOT NULL,
    sent_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    read             BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT messages_content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT messages_content_length CHECK (length(content) <= 4000)
);

-- Loading a conversation's messages in order is the hottest read path.
CREATE INDEX messages_conversation_idx ON messages (conversation_id, sent_at);

-- Unread-count queries for the notifications UI.
CREATE INDEX messages_unread_idx ON messages (conversation_id, read)
    WHERE read = FALSE;


-- ----------------------------------------------------------------------------
-- blocked_users
--
-- Universal across match types, asymmetric by row but bidirectional in effect
-- (app queries the union of both directions when filtering candidates).
-- Distinct from rejection — a block is a safety action, not a preference.
-- ----------------------------------------------------------------------------

-- reports
--
-- Moderation queue. Anyone can report anyone; admins review and act on the
-- profile (suspend, delete, no-action). reporter_id is nullable so we can
-- preserve report history if the reporter later deletes their account.
-- reported_id is NOT nullable because we RESTRICT the delete at that FK —
-- reports must be resolved before a reported user can be hard-deleted.
-- ----------------------------------------------------------------------------

CREATE TABLE reports (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id   UUID REFERENCES profiles(profile_id) ON DELETE SET NULL,
    reported_id   UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE RESTRICT,
    reason        report_reason NOT NULL,
    details       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Moderation outcome.
    reviewed_at   TIMESTAMPTZ,
    reviewed_by   TEXT,
    resolution    TEXT,  -- e.g. "suspended", "no_action", "warning_sent"

    CONSTRAINT reports_no_self CHECK (reporter_id IS NULL OR reporter_id <> reported_id),
    CONSTRAINT reports_details_length CHECK (details IS NULL OR length(details) <= 2000)
);

-- Unreviewed reports dashboard.
CREATE INDEX reports_pending_idx ON reports (created_at DESC)
    WHERE reviewed_at IS NULL;

-- "Show all reports against user X" for moderator review.
CREATE INDEX reports_reported_idx ON reports (reported_id, created_at DESC);

-- ----------------------------------------------------------------------------

CREATE TABLE blocked_users (
    blocker_id   UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    blocked_id   UUID NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    report_id    UUID REFERENCES reports(id),

    CONSTRAINT blocked_no_self CHECK (blocker_id <> blocked_id),
    PRIMARY KEY (blocker_id, blocked_id)
);

-- Reverse lookup: "who has blocked me?" — matters for matcher filtering
-- because we never suggest someone to a person they've blocked OR a person
-- who has blocked them.
CREATE INDEX blocked_users_blocked_idx ON blocked_users (blocked_id);

-- ----------------------------------------------------------------------------
-- updated_at triggers
--
-- Generic trigger function that sets NEW.updated_at = now(). Attached to the
-- tables where mutation timestamps matter for cache-busting and debugging.
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_set_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER romantic_preferences_set_updated_at
    BEFORE UPDATE ON romantic_preferences
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER roommate_preferences_set_updated_at
    BEFORE UPDATE ON roommate_preferences
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ----------------------------------------------------------------------------
-- Roles
--
-- Two roles, principle of least privilege:
--   app_user   — the FastAPI process connects as this. Full CRUD on app tables.
--   matcher_ro — the nightly matcher uses this connection when reading the
--                candidate pool. Read-only. Prevents any accidental mutation
--                from the matching path and is the right hygiene even though
--                we're no longer letting an LLM write SQL.
--
-- Passwords are placeholders. Replace before running in any environment you
-- care about — e.g. via `ALTER ROLE app_user WITH PASSWORD :'pw';` in a
-- separate bootstrap script that pulls from your secrets manager.
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD 'change_me_app';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matcher_ro') THEN
        CREATE ROLE matcher_ro LOGIN PASSWORD 'change_me_matcher';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO app_user, matcher_ro;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO matcher_ro;

-- Apply to tables created AFTER this script runs too, so future migrations
-- don't silently break the roles.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO matcher_ro;


-- ============================================================================
-- END OF SCHEMA
-- ============================================================================