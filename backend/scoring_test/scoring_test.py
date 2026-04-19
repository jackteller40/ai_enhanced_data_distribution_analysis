"""Live scoring integration test.

Pulls real seeded profiles from Postgres, converts them to the dict shape
scoring.py expects (via adapter functions), and scores pairs against each other.

Purpose: catch bugs in the "bridge" between the DB and the scorer — field name
mismatches, array-vs-scalar issues, NULL handling — that smoke tests can't find.

Run from backend/:
    python scoring_live.py
"""
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.scoring_test.scoring import score


DB_CONFIG = {
    "dbname": "foxi",
    "user": "admin",
    "password": "secret",
    "host": "127.0.0.1",
    "port": "5433",
}


# ---------------------------------------------------------------------------
# Adapters: translate DB rows into the dict shape scoring.py expects.
#
# This is where naming mismatches between schema and scorer are resolved.
# If the live test produces weird results, the bug is almost always in here.
# ---------------------------------------------------------------------------

import csv, io

def _parse_pg_array(val):
    """Parse a Postgres array that came back as a raw string.
    
    psycopg2 doesn't auto-parse custom enum arrays (like gender_preference[]).
    It returns the raw Postgres representation, e.g. '{women}' or
    '{men,"nonbinary/queer identities"}'. This turns it into a Python list.
    """
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if not isinstance(val, str):
        return val
    inner = val.strip("{}")
    if not inner:
        return []
    # csv handles quoted values with commas inside them correctly
    reader = csv.reader(io.StringIO(inner), quotechar='"')
    parts = next(reader, [])
    return [p.strip() for p in parts]


def profile_to_dict(row: dict) -> dict:
    """Convert a profiles row to scorer format."""
    # gender: the schema had this as self_gender[] originally but was changed
    # to scalar. Handle both so this script works either way without crashing.
    gender = row.get("gender")
    if isinstance(gender, list):
        gender = gender[0] if gender else None

    return {
        "gender": gender,
        "graduation_year": row.get("graduation_year"),
        "major": row.get("major"),
        "clubs": row.get("clubs") or [],
        "interests": row.get("interests") or [],
        "varsity_sports": row.get("varsity_sports") or [],
        "favorite_bar": row.get("favorite_bar"),
        "likes_going_out": row.get("likes_going_out"),
        "smokes": row.get("smokes"),
        "nicotine_lover": row.get("nicotine_lover"),
        "romantically_searching_for": row.get("romantically_searching_for"),
        "height": row.get("height"),
    }


def romantic_prefs_to_dict(row: dict) -> dict:
    """Convert a romantic_preferences row.

    Note the key rename: DB column is min_grad_yr, scorer reads min_grad_year.
    """
    if row is None:
        return {}
    return {
        "interested_in_genders": _parse_pg_array(row.get("interested_in_genders")),
        "min_grad_year": row.get("min_grad_yr"),
        "max_grad_year": row.get("max_grad_yr"),
        "min_preferred_height": row.get("min_preferred_height"),
        "max_preferred_height": row.get("max_preferred_height"),
    }


def roommate_prefs_to_dict(row: dict) -> dict:
    if row is None:
        return {}
    return {
        "roommate_gender_preference": row.get("roommate_gender_preference"),
        "sleep_schedule": row.get("sleep_schedule"),
        "cleanliness": row.get("cleanliness"),
        "noise_tolerance": row.get("noise_tolerance"),
        "has_pets": row.get("has_pets"),
        "ok_with_pets": row.get("ok_with_pets"),
        "guests_frequency": row.get("guests_frequency"),
        "on_campus": row.get("on_campus"),
    }


# ---------------------------------------------------------------------------
# The live test
# ---------------------------------------------------------------------------


def run():
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    # Pull up to 10 profiles with their romantic preferences.
    cur.execute("""
        SELECT
            p.profile_id, p.display_name, p.gender, p.graduation_year,
            p.major, p.clubs, p.interests, p.varsity_sports,
            p.favorite_bar, p.likes_going_out, p.smokes, p.nicotine_lover,
            p.height, p.romantically_searching_for,
            rp.interested_in_genders, rp.min_grad_yr, rp.max_grad_yr,
            rp.priority_weights AS romantic_weights
        FROM profiles p
        LEFT JOIN romantic_preferences rp ON p.profile_id = rp.profile_id
        LIMIT 10;
    """)
    profiles = cur.fetchall()

    if len(profiles) < 2:
        print("ERROR: need at least 2 profiles in the DB to test. Run seed.py first.")
        return

    print(f"Loaded {len(profiles)} profiles.\n")

    # Score every pair of profiles against each other for romantic matching.
    # This gives us N*(N-1)/2 data points to eyeball.
    print("=" * 70)
    print("ROMANTIC MATCH SCORES (receiver -> candidate)")
    print("=" * 70)

    for i, receiver in enumerate(profiles):
        r_dict = profile_to_dict(receiver)
        r_prefs = romantic_prefs_to_dict(receiver)
        weights = receiver.get("romantic_weights") or {}

        print(f"\n{receiver['display_name']} "
              f"(gender={r_dict['gender']}, "
              f"wants={r_prefs.get('interested_in_genders')}, "
              f"grad={r_dict['graduation_year']})")

        for j, candidate in enumerate(profiles):
            if i == j:
                continue
            c_dict = profile_to_dict(candidate)
            c_prefs = romantic_prefs_to_dict(candidate)

            s = score(
                receiver=r_dict,
                receiver_prefs=r_prefs,
                candidate=c_dict,
                candidate_prefs=c_prefs,
                match_type="romantic",
                weights=weights,
            )

            marker = "  " if s == 0.0 else "->"
            print(f"  {marker} {candidate['display_name']:25s} "
                  f"gender={c_dict['gender']:12s} "
                  f"score={s:.3f}")

    # Also a roommate run, but less verbose.
    cur.execute("""
        SELECT
            p.profile_id, p.display_name, p.gender, p.graduation_year,
            p.major, p.clubs, p.interests, p.varsity_sports,
            p.favorite_bar, p.likes_going_out, p.smokes, p.nicotine_lover,
            p.height, p.romantically_searching_for,
            rmp.roommate_gender_preference, rmp.sleep_schedule,
            rmp.cleanliness, rmp.noise_tolerance, rmp.has_pets, rmp.ok_with_pets,
            rmp.guests_frequency, rmp.on_campus,
            rmp.priority_weights AS roommate_weights
        FROM profiles p
        LEFT JOIN roommate_preferences rmp ON p.profile_id = rmp.profile_id
        LIMIT 5;
    """)
    rm_profiles = cur.fetchall()

    print("\n" + "=" * 70)
    print("ROOMMATE MATCH SCORES (first profile vs. all others)")
    print("=" * 70)
    if rm_profiles:
        receiver = rm_profiles[0]
        r_dict = profile_to_dict(receiver)
        r_prefs = roommate_prefs_to_dict(receiver)
        weights = receiver.get("roommate_weights") or {}
        print(f"\nReceiver: {receiver['display_name']} "
              f"(cleanliness={r_prefs.get('cleanliness')}, "
              f"sleep={r_prefs.get('sleep_schedule')})")
        for candidate in rm_profiles[1:]:
            c_dict = profile_to_dict(candidate)
            c_prefs = roommate_prefs_to_dict(candidate)
            s = score(
                receiver=r_dict,
                receiver_prefs=r_prefs,
                candidate=c_dict,
                candidate_prefs=c_prefs,
                match_type="roommate",
                weights=weights,
            )
            print(f"  -> {candidate['display_name']:25s} "
                  f"cleanliness={c_prefs.get('cleanliness')} "
                  f"sleep={c_prefs.get('sleep_schedule'):12s} "
                  f"score={s:.3f}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run()