"""
NOTE: This test file requires a separate Postgres database called 'swipetest'
with a minimal schema containing just: profiles, suggestions, rejected_matches,
active_matches, conversations.

Running this against the main 'foxi' database would wipe your seed data —
the tests call TRUNCATE on the working tables before each group.

Setup (post-demo cleanup task):
  createdb swipetest
  psql swipetest -f path/to/test_schema.sql

The test_schema.sql needed is a subset of schema.sql — just the tables touched
by swipe.py. Not included in this commit.
"""

"""Integration tests for swipe.py against a real Postgres DB.
 
Covers:
  - handle_like: one-sided (no reverse), mutual (with reverse), idempotent
  - handle_reject: symmetric rejection rows, suggestion deletion,
                   reverse-direction suggestion cleanup
  - validation: unknown suggestion, wrong receiver
  - active_matches ordering constraint respected
"""
import sys
sys.path.insert(0, "/home/claude")
 
from uuid import UUID
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
 
from swipe import handle_like, handle_reject
 
DB_URL = "postgresql+psycopg2://postgres:test@localhost:5432/swipetest"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
 
 
def reset():
    with engine.begin() as c:
        c.execute(text("TRUNCATE conversations, active_matches, rejected_matches, suggestions, profiles RESTART IDENTITY CASCADE"))
 
 
def make_users(n=2):
    with engine.begin() as c:
        ids = []
        for i in range(n):
            r = c.execute(text("INSERT INTO profiles (display_name) VALUES (:n) RETURNING profile_id"), {"n": f"User{i}"}).scalar()
            ids.append(r)
        return ids
 
 
def make_suggestion(receiver, candidate, match_type="romantic", status="pending"):
    with engine.begin() as c:
        return c.execute(text("""
            INSERT INTO suggestions (receiver_id, candidate_id, match_type, status)
            VALUES (:r, :c, :m, :s) RETURNING id
        """), {"r": receiver, "c": candidate, "m": match_type, "s": status}).scalar()
 
 
def count(table, where=""):
    with engine.begin() as c:
        q = f"SELECT COUNT(*) FROM {table}"
        if where:
            q += f" WHERE {where}"
        return c.execute(text(q)).scalar()
 
 
def status_of(sug_id):
    with engine.begin() as c:
        return c.execute(text("SELECT status FROM suggestions WHERE id = :i"), {"i": sug_id}).scalar()
 
 
# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
 
results = []
 
def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
 
 
# Test 1: handle_like on a pending suggestion with no reverse like -> 'liked'
reset()
alice, bob = make_users(2)
sug_id = make_suggestion(alice, bob, "romantic")
 
s = Session()
r = handle_like(s, sug_id, alice)
s.close()
 
check("1a. one-sided like returns status='liked'", r.status == "liked")
check("1b. suggestion status is now 'liked'", status_of(sug_id) == "liked")
check("1c. no active_match created", count("active_matches") == 0)
check("1d. no conversation created", count("conversations") == 0)
 
# Test 2: handle_like completes a mutual match
reset()
alice, bob = make_users(2)
# Bob already liked Alice
bob_sug = make_suggestion(bob, alice, "romantic", status="liked")
# Alice now has a suggestion for Bob and likes him
alice_sug = make_suggestion(alice, bob, "romantic")
 
s = Session()
r = handle_like(s, alice_sug, alice)
s.close()
 
check("2a. mutual like returns status='matched'", r.status == "matched")
check("2b. active_match_id is returned", r.active_match_id is not None)
check("2c. active_matches row exists", count("active_matches") == 1)
check("2d. conversation row exists", count("conversations") == 1)
check("2e. alice's suggestion is 'matched'", status_of(alice_sug) == "matched")
check("2f. bob's suggestion is 'matched'", status_of(bob_sug) == "matched")
 
# Test 2g: profile_id_a < profile_id_b constraint was satisfied
with engine.begin() as c:
    row = c.execute(text("SELECT profile_id_a, profile_id_b FROM active_matches")).first()
check("2g. active_matches has ordered UUIDs (a < b)", row[0] < row[1])
 
 
# Test 3: idempotent like (already liked)
reset()
alice, bob = make_users(2)
sug_id = make_suggestion(alice, bob, "romantic", status="liked")
 
s = Session()
r = handle_like(s, sug_id, alice)
s.close()
 
check("3a. second like on 'liked' returns noop", r.status == "noop")
check("3b. status still 'liked'", status_of(sug_id) == "liked")
check("3c. no active_match created", count("active_matches") == 0)
 
 
# Test 4: liking someone else's suggestion fails
reset()
alice, bob = make_users(2)
sug_id = make_suggestion(alice, bob, "romantic")
carol_id = UUID("00000000-0000-0000-0000-000000000099")
 
s = Session()
try:
    handle_like(s, sug_id, carol_id)
    check("4. wrong-receiver like rejected", False, "no exception raised")
except ValueError as e:
    check("4. wrong-receiver like rejected", True, f"got ValueError: {e}")
s.close()
 
 
# Test 5: liking unknown suggestion
reset()
alice, _ = make_users(2)
 
s = Session()
try:
    handle_like(s, UUID("00000000-0000-0000-0000-000000000000"), alice)
    check("5. unknown suggestion rejected", False, "no exception")
except ValueError:
    check("5. unknown suggestion rejected", True)
s.close()
 
 
# Test 6: reject writes symmetric rows and deletes suggestion
reset()
alice, bob = make_users(2)
sug_id = make_suggestion(alice, bob, "romantic")
 
s = Session()
handle_reject(s, sug_id, alice)
s.close()
 
check("6a. suggestion deleted", count("suggestions") == 0)
check("6b. two rejected_matches rows written",
      count("rejected_matches") == 2)
check("6c. alice->bob rejection exists",
      count("rejected_matches", f"rejecter_id = '{alice}' AND rejected_id = '{bob}'") == 1)
check("6d. bob->alice rejection exists",
      count("rejected_matches", f"rejecter_id = '{bob}' AND rejected_id = '{alice}'") == 1)
 
 
# Test 7: reject cleans up reverse-direction 'liked' suggestion
reset()
alice, bob = make_users(2)
bob_sug = make_suggestion(bob, alice, "romantic", status="liked")  # bob liked alice
alice_sug = make_suggestion(alice, bob, "romantic")  # alice now sees bob
 
s = Session()
handle_reject(s, alice_sug, alice)  # alice rejects bob
s.close()
 
check("7a. alice's suggestion deleted", count("suggestions", f"id = '{alice_sug}'") == 0)
check("7b. bob's reverse suggestion also deleted", count("suggestions", f"id = '{bob_sug}'") == 0)
check("7c. two symmetric rejections written", count("rejected_matches") == 2)
 
 
# Test 8: reject only affects THIS match_type, not others
reset()
alice, bob = make_users(2)
rom_sug = make_suggestion(alice, bob, "romantic")
rm_sug = make_suggestion(alice, bob, "roommate")
 
s = Session()
handle_reject(s, rom_sug, alice)
s.close()
 
check("8a. romantic suggestion deleted", count("suggestions", f"id = '{rom_sug}'") == 0)
check("8b. roommate suggestion survives", count("suggestions", f"id = '{rm_sug}'") == 1)
check("8c. only romantic rejections written",
      count("rejected_matches", "match_type = 'romantic'") == 2)
check("8d. no roommate rejections",
      count("rejected_matches", "match_type = 'roommate'") == 0)
 
 
# Test 9: wrong-receiver reject rejected
reset()
alice, bob = make_users(2)
sug_id = make_suggestion(alice, bob, "romantic")
carol_id = UUID("00000000-0000-0000-0000-000000000099")
 
s = Session()
try:
    handle_reject(s, sug_id, carol_id)
    check("9. wrong-receiver reject rejected", False, "no exception")
except ValueError:
    check("9. wrong-receiver reject rejected", True)
s.close()
 
 
# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
print()
fails = [r for r in results if not r[0]]
print(f"{len(results)} tests, {len(fails)} failed")
if fails:
    for _, name, detail in fails:
        print(f"  FAIL {name}  {detail}")
    sys.exit(1)