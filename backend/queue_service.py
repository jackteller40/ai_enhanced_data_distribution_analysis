import csv, io, json
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from scoring import score

def _parse_pg_array(val):
    #parse postgres enum arrays that come back as strings like '{women}'
    if val is None: return None
    if isinstance(val, list): return val
    if not isinstance(val, str): return val
    inner = val.strip("{}")
    if not inner: return []
    reader = csv.reader(io.StringIO(inner), quotechar = '"')
    return [p.strip() for p in next(reader, [])]

def profile_to_dict(row) -> dict:
    gender = row.get("gender")
    #convert a profile's row into the shape scoring.py expects
    if isinstance(gender, list):
        gender = gender[0] if gender else None
    return{
        "gender": gender,
        "graduation_year": row.get("graduation_year"),
        "major": row.get("major"),
        "clubs": _parse_pg_array(row.get("clubs")),
        "interests": _parse_pg_array(row.get("interests")),
        "varsity_sports": _parse_pg_array(row.get("varsity_sports")),
        "likes_going_out": row.get("likes_going_out"),
        "favorite_bar": row.get("favorite_bar"),
        "smokes": row.get("smokes"),
        "nicotine_lover": row.get("nicotine_lover"),
        "romantically_searching_for": row.get("romantically_searching_for"),
        "height": row.get("height")
    }
    
def romantic_prefs_to_dict(row) -> dict:
    if row is None: return {}
    return {
        "interested_in_genders": _parse_pg_array(row.get("interested_in_genders")),
        "min_grad_year": row.get("min_grad_yr"),
        "max_grad_year": row.get("max_grad_yr"),
        "min_preferred_height": row.get("min_preferred_height"),
        "max_preferred_height": row.get("max_preferred_height")
    }
    
def roommate_prefs_to_dict(row) -> dict:
    if row is None: return {}
    return {
        "roommate_gender_preference": row.get("roommate_gender_preference"),
        "sleep_schedule": row.get("sleep_schedule"),
        "cleanliness": row.get("cleanliness"),
        "noise_tolerance": row.get("noise_tolerance"),
        "has_pets": row.get("has_pets"),
        "guests_frequency": row.get("guests_frequency"),
        "on_campus": row.get("on_campus")
    }

def _parse_weights(val):
    #JSONB priority_weights can come back as dict or string depending on psycopg2
    if val is None: return {}
    if isinstance(val, str): return json.loads(val)
    return val

def get_queue(receiver_id: UUID, match_type: str, db: Session, limit: int = 10):
    # main entry point, returns sorted kist of suggestions with scores
    if match_type not in ("romantic", "roommate"):
        raise ValueError(f"invalid match_type: {match_type}")
    
    prefs_table = "romantic_preferences" if match_type == "romantic" else "roommate_preferences"
    prefs_adapter = romantic_prefs_to_dict if match_type == "romantic" else roommate_prefs_to_dict
    
    #1: receiver
    receiver_row = db.execute(
        text("SELECT * FROM profiles WHERE profile_id = :id"),
        {"id": receiver_id}
    ).mappings().first()
    
    '''
    if receiver_row is None:
        raise ValueError("receiver profile not found")
    '''
    
    receiver_prefs_row = db.execute(
        text(f"SELECT * FROM {prefs_table} WHERE profile_id = :id"),
        {"id": receiver_id}
    ).mappings().first()
    
    if not receiver_row or not receiver_prefs_row:
        return []
    
    weights = _parse_weights(receiver_prefs_row.get("priority_weights"))
    
    #2: candidate pool
    candidate_rows = db.execute(
        text("""
             SELECT p.*
             FROM profiles p
             WHERE p.profile_id <> :me
                AND p.status = 'active'
                AND :match_type = ANY(p.looking_for)
                AND NOT EXISTS (
                    SELECT 1 FROM blocked_users b
                    WHERE (b.blocker_id = :me AND b.blocked_id = p.profile_id)
                        OR (b.blocker_id = p.profile_id AND b.blocked_id = :me)
                )AND NOT EXISTS (
                    SELECT 1 FROM rejected_matches r
                    WHERE r.match_type = :match_type AND (
                    (r.rejecter_id = :me AND r.rejected_id = p.profile_id)
                    OR (r.rejected_id = :me AND r.rejecter_id = p.profile_id))
                )
                LIMIT 100
                """),
        {"me": receiver_id, "match_type": match_type}
    ).mappings().all()
     
    if not candidate_rows:
        return []
    
    candidate_ids = [c["profile_id"] for c in candidate_rows]
    cp_rows = db.execute(
        text(f"SELECT * FROM {prefs_table} WHERE profile_id = ANY(:ids)"),
        {"ids": candidate_ids}
    ).mappings().all()
    prefs_by_id = {r["profile_id"]: r for r in cp_rows}
    
    #3: score
    
    receiver_dict = profile_to_dict(receiver_row)
    receiver_prefs_dict = prefs_adapter(receiver_prefs_row)
    
    scored = []
    for c in candidate_rows:
        c_prefs_row = prefs_by_id.get(c["profile_id"])
        if not c_prefs_row:
            continue
        try:
            s = score(
                receiver = receiver_dict,
                receiver_prefs = receiver_prefs_dict,
                candidate = profile_to_dict(c),
                candidate_prefs = prefs_adapter(c_prefs_row),
                match_type = match_type,
                weights = weights
            )
        except Exception as e:
            continue
        if s <= 0.0: continue
        scored.append((c, s))
        
    scored.sort(key = lambda x: x[1], reverse = True)
    top = scored[:limit]
    
    #4: upsert into suggestions so /like and /reject have IDs to reference
    suggestions_out = []
    for c, s in top:
        sug_id = db.execute(
            text("""
                 INSERT INTO suggestions (receiver_id, candidate_id, match_type, status, match_score)
                 VALUES (:r, :c, :m, 'pending', :score)
                 ON CONFLICT (receiver_id, candidate_id, match_type)
                    DO UPDATE SET match_score = EXCLUDED.match_score
                RETURNING id
            """),
            {"r": receiver_id, "c": c["profile_id"], "m": match_type, "score": s}
        ).scalar()
        suggestions_out.append({
            "id": str(sug_id),
            "agent_explanation": None,
            "match_score": round(s, 3),
            "candidate_profile": {
                "display_name": c["display_name"],
                "graduation_year": c["graduation_year"],
                "major": c["major"],
                "bio": c["bio"],
                "likes_going_out": c["likes_going_out"],
                "clubs": list(c["clubs"] or []),
                "photos": [],
            }
        })
        
    db.commit()
    return suggestions_out