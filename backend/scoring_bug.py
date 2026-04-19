"""Debug what's in the DB rows and what the scorer sees."""
import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONFIG = {"dbname": "foxi", "user": "admin", "password": "secret",
             "host": "127.0.0.1", "port": "5433"}

conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
cur = conn.cursor()

cur.execute("""
    SELECT p.display_name, p.gender, p.graduation_year, p.major, p.clubs,
           p.smokes,
           rp.interested_in_genders, rp.min_grad_yr, rp.max_grad_yr,
           rp.priority_weights
    FROM profiles p
    LEFT JOIN romantic_preferences rp ON p.profile_id = rp.profile_id
    LIMIT 2;
""")
rows = cur.fetchall()

for row in rows:
    print(f"\n=== {row['display_name']} ===")
    for key, val in row.items():
        print(f"  {key!r:30s} = {val!r}  (type: {type(val).__name__})")