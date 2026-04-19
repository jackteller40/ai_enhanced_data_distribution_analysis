import csv, io, json
from uuid import UUID
from sqlalchemy import text
from sqlalchemy import Session
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
    #convert a profile's row into the shape scoring.py expects
    gender = row.gender
    if isinstance(gender, list):
        gender = gender[0] if gender else None
    return{
        "gender": gender,
        "graduation_year": row.graduation_year,
        "major": row.major,
        "clubs": row.clubs or [],
        "interests": row.interests or [],
        "varisty_sports": row.varsity_sports or [],
        "favorite_bar": row.favorite_bar,
        "smokes": row.smokes,
        "nicotine_lover": row.nicotine_lover,
        "romantically_searching_for": row.romantically_searching_for,
        "height": row.height
    }
    
def romantic_prefs_to_dict(row) -> dict:
    if row is None: return {}
    return {
        "interested_in_genders": _parse_pg_array(row.interested_in_genders),
        "min_grad_year": row.min_grad_yr,
        "max_grad_year": row.max_grad_yr,
        "min_preferred_height": getattr(row, "min_preferred_height", None),
        "max_preferred_height": getattr(row, "max_preferred_height", None)
    }
    
def roomate_prefs_to_dict(row) -> dict:
    if row is None: return {}
    return {
        "roomate_gender_preference": row.roomate_gender_preference,
        "sleep_schedule": row.sleep_schedule,
        "cleanliness": row.cleanliness,
        "noise_tolerance": row.noise_tolerance,
        "has_pets": row.has_pets,
        "guests_frequency": row.guests_frequency,
        "on_campus": row.on_campus
    }
    
def _parse_weights(val):
    #JSONB priority_weights can come back as dict or string depending on psycopg2
    if val is None: return {}
    if isinstance(val, str): return json.loads(val)
    return val

def get_queue(receiver_id: UUID, match_type: str, db: Session, limit: int = 10):
    # main entry point, returns sorted kist of suggestions with scores
    if match_type not in ("romantic", "roomate"):
        raise ValueError(f"invalid match_type: {match_type}")
    
    prefs_table = "romantic_preferences" if match_type == "romantic" else "roomate_preferences"
    prefs_adapter = romantic_prefs_to_dict if match_type == "romantic" else roomate_prefs_to_dict