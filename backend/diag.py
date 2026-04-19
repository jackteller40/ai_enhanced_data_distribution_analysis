import psycopg2
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(dbname='foxi', user='admin', password='secret', host='127.0.0.1', port='5433')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT p.profile_id, p.gender, p.graduation_year, p.status, p.looking_for,
           rp.interested_in_genders, rp.priority_weights
    FROM profiles p
    JOIN romantic_preferences rp ON p.profile_id = rp.profile_id
    WHERE p.gender = 'woman'
    AND 'romantic' = ANY(p.looking_for)
    AND p.status = 'active'
    LIMIT 1
""")
row = cur.fetchone()
for k, v in row.items():
    print(f"  {k}: {v}  ({type(v).__name__})")
conn.close()
