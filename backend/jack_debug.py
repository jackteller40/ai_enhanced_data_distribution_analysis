import psycopg2
from psycopg2.extras import RealDictCursor
import csv, io, json
from scoring import score

DB = {"dbname": "foxi", "user": "admin", "password": "secret",
      "host": "127.0.0.1", "port": "5433"}

def _parse_pg_array(val):
    if val is None: return None
    if isinstance(val, list): return val
    if not isinstance(val, str): return val
    inner = val.strip("{}")
    if not inner: return []
    reader = csv.reader(io.StringIO(inner), quotechar='"')
    return [p.strip() for p in next(reader, [])]

conn = psycopg2.connect(**DB, cursor_factory=RealDictCursor)
cur = conn.cursor()

cur.execute("""
    SELECT p.*, rp.interested_in_genders, rp.min_grad_yr, rp.max_grad_yr,
           rp.priority_weights
    FROM profiles p
    JOIN romantic_preferences rp ON p.profile_id = rp.profile_id
    WHERE p.profile_id = '3afe844c-1045-4693-a596-60f8c291bdff'
""")
receiver = cur.fetchone()
print(f"Receiver: {receiver['display_name']}")
print(f"  gender: {receiver['gender']}")
print(f"  grad year: {receiver['graduation_year']}")
print(f"  interested_in_genders parsed: {_parse_pg_array(receiver['interested_in_genders'])}")
print(f"  weights: {receiver['priority_weights']}")
print()

receiver_dict = {
    "gender": receiver["gender"],
    "graduation_year": receiver["graduation_year"],
    "major": receiver["major"],
    "clubs": _parse_pg_array(receiver["clubs"]),
    "interests": _parse_pg_array(receiver["interests"]),
    "varsity_sports": _parse_pg_array(receiver["varsity_sports"]),
    "likes_going_out": receiver["likes_going_out"],
    "favorite_bar": receiver["favorite_bar"],
    "smokes": receiver["smokes"],
    "nicotine_lover": receiver["nicotine_lover"],
    "romantically_searching_for": receiver["romantically_searching_for"],
    "height": receiver["height"],
}
receiver_prefs = {
    "interested_in_genders": _parse_pg_array(receiver["interested_in_genders"]),
    "min_grad_year": receiver["min_grad_yr"],
    "max_grad_year": receiver["max_grad_yr"],
}
weights = receiver["priority_weights"] or {}

cur.execute("""
    SELECT p.*, rp.interested_in_genders, rp.min_grad_yr, rp.max_grad_yr,
           rp.priority_weights
    FROM profiles p
    JOIN romantic_preferences rp ON p.profile_id = rp.profile_id
    WHERE p.profile_id <> '3afe844c-1045-4693-a596-60f8c291bdff'
      AND p.status = 'active'
      AND 'romantic' = ANY(p.looking_for)
      AND p.gender = 'woman'
    LIMIT 5
""")
candidates = cur.fetchall()
print(f"Pulled {len(candidates)} candidates:\n")

for c in candidates:
    c_dict = {
        "gender": c["gender"],
        "graduation_year": c["graduation_year"],
        "major": c["major"],
        "clubs": _parse_pg_array(c["clubs"]),
        "interests": _parse_pg_array(c["interests"]),
        "varsity_sports": _parse_pg_array(c["varsity_sports"]),
        "likes_going_out": c["likes_going_out"],
        "favorite_bar": c["favorite_bar"],
        "smokes": c["smokes"],
        "nicotine_lover": c["nicotine_lover"],
        "romantically_searching_for": c["romantically_searching_for"],
        "height": c["height"],
    }
    c_prefs = {
        "interested_in_genders": _parse_pg_array(c["interested_in_genders"]),
        "min_grad_year": c["min_grad_yr"],
        "max_grad_year": c["max_grad_yr"],
    }
    s = score(
        receiver=receiver_dict,
        receiver_prefs=receiver_prefs,
        candidate=c_dict,
        candidate_prefs=c_prefs,
        match_type="romantic",
        weights=weights,
    )
    print(f"  {c['display_name']:25s} grad={c['graduation_year']} "
          f"cand_wants={c_prefs['interested_in_genders']} score={s:.3f}")

conn.close()
