"""Live integration test for swipe.py against the foxi database.
 
Runs real scenarios (one-sided like, mutual like, reject) against your
actually-seeded Postgres, then ROLLS BACK everything so your seed data
survives unchanged.
 
How the rollback works:
    swipe.py calls db.commit() internally. If we just opened a session and
    called it, those commits would persist. The trick is wrapping each test
    in an outer transaction — when swipe.py calls commit(), SQLAlchemy
    actually commits to a SAVEPOINT rather than the real transaction, and
    our outer rollback discards everything.
 
Run from backend/:
    python swipe_live.py
"""
import sys
from uuid import uuid4
 
import psycopg2
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
 
from swipe import handle_like, handle_reject
 
 
DB_URL = "postgresql+psycopg2://admin:secret@127.0.0.1:5433/foxi"
 
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
 
 
# ----------------------------------------------------------------------------
# The rollback trick: open an outer transaction, then start a SAVEPOINT.
# When swipe.py's internal commit() fires, it commits only to the savepoint.
# We rollback the outer transaction at the end and nothing persists.
# ----------------------------------------------------------------------------
 
class RollbackSession:
    """Context manager that yields a session whose commits never persist."""
    def __enter__(self):
        self.connection = engine.connect()
        self.trans = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        return self.session
 
    def __exit__(self, *args):
        self.session.close()
        self.trans.rollback()   # <-- discards ALL writes done during the test
        self.connection.close()
 
 
# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
 
def get_two_profile_ids(session):
    """Pull two real profile_ids from the DB to test with."""
    rows = session.execute(
        text("SELECT profile_id FROM profiles LIMIT 2")
    ).fetchall()
    if len(rows) < 2:
        raise RuntimeError("Need at least 2 profiles in DB. Run seed.py first.")
    return rows[0][0], rows[1][0]
 
 
def count_baseline(conn, table):
    """Count rows in a table via a fresh connection (outside any test txn)."""
    with engine.connect() as c:
        return c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
 
 
def make_suggestion(session, receiver, candidate, match_type="romantic", status="pending"):
    return session.execute(text("""
        INSERT INTO suggestions (receiver_id, candidate_id, match_type, status)
        VALUES (:r, :c, :m, :s) RETURNING id
    """), {"r": receiver, "c": candidate, "m": match_type, "s": status}).scalar()
 
 
def count_in_session(session, table, where=""):
    q = f"SELECT COUNT(*) FROM {table}"
    if where:
        q += f" WHERE {where}"
    return session.execute(text(q)).scalar()
 
 
def status_of(session, sug_id):
    return session.execute(
        text("SELECT status FROM suggestions WHERE id = :i"), {"i": sug_id}
    ).scalar()
 
 
# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
 
results = []
 
def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
 
 
# -- BASELINE COUNTS --
# Take snapshots BEFORE running tests. These should be unchanged AFTER.
baseline = {
    "profiles": count_baseline(engine, "profiles"),
    "suggestions": count_baseline(engine, "suggestions"),
    "rejected_matches": count_baseline(engine, "rejected_matches"),
    "active_matches": count_baseline(engine, "active_matches"),
    "conversations": count_baseline(engine, "conversations"),
}
print(f"Baseline: {baseline}\n")
 
 
# -- TEST 1: one-sided like (pending -> liked, no match created) --
print("--- Test 1: one-sided like ---")
with RollbackSession() as session:
    alice, bob = get_two_profile_ids(session)
    sug_id = make_suggestion(session, alice, bob)
    session.commit()
 
    result = handle_like(session, sug_id, alice)
 
    check("1a. status='liked'", result.status == "liked")
    check("1b. no active_match_id", result.active_match_id is None)
    check("1c. suggestion is now 'liked'", status_of(session, sug_id) == "liked")
    check("1d. no active_matches created", count_in_session(session, "active_matches") == 0)
 
 
# -- TEST 2: mutual match (creates active_match + conversation) --
print("\n--- Test 2: mutual like ---")
with RollbackSession() as session:
    alice, bob = get_two_profile_ids(session)
    # Bob already liked Alice
    bob_sug = make_suggestion(session, bob, alice, status="liked")
    # Now Alice has a suggestion for Bob
    alice_sug = make_suggestion(session, alice, bob)
    session.commit()
 
    am_before = count_in_session(session, "active_matches")
 
    result = handle_like(session, alice_sug, alice)
 
    check("2a. status='matched'", result.status == "matched")
    check("2b. active_match_id returned", result.active_match_id is not None)
    check("2c. one new active_match created",
          count_in_session(session, "active_matches") == am_before + 1)
    check("2d. conversation created",
          count_in_session(session, "conversations",
                           f"active_match_id = '{result.active_match_id}'") == 1)
    check("2e. alice's suggestion now 'matched'",
          status_of(session, alice_sug) == "matched")
    check("2f. bob's suggestion also 'matched'",
          status_of(session, bob_sug) == "matched")
 
 
# -- TEST 3: idempotent like (already-liked stays liked, returns noop) --
print("\n--- Test 3: idempotent like ---")
with RollbackSession() as session:
    alice, bob = get_two_profile_ids(session)
    sug_id = make_suggestion(session, alice, bob, status="liked")
    session.commit()
 
    result = handle_like(session, sug_id, alice)
 
    check("3a. returns noop", result.status == "noop")
    check("3b. status still 'liked'", status_of(session, sug_id) == "liked")
 
 
# -- TEST 4: reject (symmetric rows written, suggestion deleted) --
print("\n--- Test 4: reject ---")
with RollbackSession() as session:
    alice, bob = get_two_profile_ids(session)
    sug_id = make_suggestion(session, alice, bob)
    session.commit()
 
    rej_before = count_in_session(session, "rejected_matches")
 
    handle_reject(session, sug_id, alice)
 
    check("4a. suggestion deleted",
          count_in_session(session, "suggestions", f"id = '{sug_id}'") == 0)
    check("4b. two rejected_matches rows added",
          count_in_session(session, "rejected_matches") == rej_before + 2)
    check("4c. alice -> bob rejection exists",
          count_in_session(session, "rejected_matches",
                           f"rejecter_id = '{alice}' AND rejected_id = '{bob}'") >= 1)
    check("4d. bob -> alice rejection exists",
          count_in_session(session, "rejected_matches",
                           f"rejecter_id = '{bob}' AND rejected_id = '{alice}'") >= 1)
 
 
# -- TEST 5: wrong-receiver rejected --
print("\n--- Test 5: wrong receiver ---")
with RollbackSession() as session:
    alice, bob = get_two_profile_ids(session)
    sug_id = make_suggestion(session, alice, bob)
    session.commit()
 
    fake_user = uuid4()
    try:
        handle_like(session, sug_id, fake_user)
        check("5. wrong receiver rejected", False, "no exception raised")
    except ValueError:
        check("5. wrong receiver rejected", True)
 
 
# ----------------------------------------------------------------------------
# Verify rollback actually worked — DB state unchanged
# ----------------------------------------------------------------------------
 
print("\n--- Verifying rollback preserved DB state ---")
after = {
    "profiles": count_baseline(engine, "profiles"),
    "suggestions": count_baseline(engine, "suggestions"),
    "rejected_matches": count_baseline(engine, "rejected_matches"),
    "active_matches": count_baseline(engine, "active_matches"),
    "conversations": count_baseline(engine, "conversations"),
}
print(f"After:    {after}")
 
for table, before_count in baseline.items():
    check(f"DB unchanged: {table}", after[table] == before_count,
          f"before={before_count}, after={after[table]}")
 
 
# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
print()
fails = [r for r in results if not r[0]]
print(f"{len(results)} checks, {len(fails)} failed")
if fails:
    for _, name, detail in fails:
        print(f"  FAIL {name}  {detail}")
    sys.exit(1)