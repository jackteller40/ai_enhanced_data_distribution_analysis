from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
import models, schemas, auth, profile, conversation
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MatchApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────

@app.post("/signup", response_model=schemas.TokenResponse, status_code=201)
def signup(body: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.Account).filter(models.Account.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    account = models.Account(
        email=body.email,
        password_hash=auth.hash_password(body.password)
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    token = auth.create_access_token({"sub": str(account.profile_id)})
    return {"access_token": token}


@app.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.email == body.email).first()
    if not account or not auth.verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_access_token({"sub": str(account.profile_id)})
    return {"access_token": token}


@app.delete("/account", status_code=204)
def delete_account(
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    db.delete(current_user)
    db.commit()


# ── Profile ───────────────────────────────────────

@app.put("/profile", response_model=schemas.ProfileResponse)
def update_profile(
    body: schemas.ProfileSetupRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return profile.upsert_profile(current_user, body, db)


@app.get("/profile/me", response_model=schemas.ProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return profile.get_profile(current_user.profile_id, db)


# ── Conversation ──────────────────────────────────

@app.post("/conversations", response_model=schemas.ConversationResponse, status_code=201)
def create_conversation(
    active_match_id: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return conversation.create_conversation(active_match_id, db)


@app.post("/conversations/{conversation_id}/messages", response_model=schemas.MessageResponse, status_code=201)
def send_message(
    conversation_id: str,
    body: schemas.SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return conversation.send_message(current_user, conversation_id, body, db)


@app.get("/conversations/{conversation_id}/messages", response_model=list[schemas.MessageResponse])
def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return conversation.get_messages(conversation_id, db)


@app.post("/conversations/{conversation_id}/read", status_code=204)
def mark_read(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    conversation.mark_read(current_user, conversation_id, db)
    
# ── Swipe ──────────────────────────────────

@app.post("/suggestions/{suggestion_id}/like", response_model=schemas.LikeResponse)
def like_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    from swipe import handle_like
    from uuid import UUID
    try:
        result = handle_like(db, UUID(suggestion_id), current_user.profile_id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code = 404, detail = str(e))
    return {
        "status": result.status,
        "active_match_id": str(result.active_match_id) if result.active_match_id else None
    }
    
@app.post("/suggestions/{suggestion_id}/reject", status_code = 204)
def reject_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    from swipe import handle_reject
    from uuid import UUID
    try:
        handle_reject(db, UUID(suggestion_id), current_user.profile_id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code = 404, detail = str(e))
    
# ── Queue ──────────────────────────────────

@app.get("/queue", response_model = list[schemas.SuggestionResponse])
def get_queue(
    match_type: str,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    from queue_service import get_queue as build_queue
    try:
        return build_queue(current_user.profile_id, match_type, db)
    except ValueError as e:
        raise HTTPException(status_code = 400, detail = str(e))
    
# ── Preferences ──────────────────────────────────

import preferences

@app.put("/preferences/romantic", response_model = schemas.RomanticPreferencesResponse)
def set_romantic_preferences(
    body: schemas.RomanticPreferencesRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    return preferences.upsert_romantic_preferences(current_user, body, db)

@app.put("/preferences/roommate", response_model = schemas.RoommatePreferencesResponse)
def set_roommate_preferences(
    body: schemas.RoommatePreferencesRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    return preferences.upsert_roommate_preferences(current_user, body, db)

# ── Matches ──────────────────────────────────
@app.get("/matches", response_model = list[schemas.MatchResponse])
def get_matches(
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user)
):
    rows = db.execute(
        text("""
             SELECT am.id, am.match_type, am.matched_at,
                    am.profile_id_a, am.profile_id_b,
                    p_a.display_name AS name_a,
                    p_b.display_name AS name_b,
                    c.id AS conversation_id
             FROM active_matches am
             JOIN profiles p_a ON am.profile_id_a = p_a.profile_id
             JOIN profiles p_b ON am.profile_id_b = p_b.profile_id
             LEFT JOIN conversations c ON c.active_match_id = am.id
             WHERE :me IN (am.profile_id_a, am.profile_id_b)
             ORDER BY am.matched_at DESC
        """),
        {"me": current_user.profile_id}
    ).mappings().all()
    
    out = []
    for r in rows:
        if r["profile_id_a"] == current_user.profile_id:
            other_id, other_name = r["profile_id_b"], r["name_b"]
        else:
            other_id, other_name = r["profile_id_a"], r["name_a"]
        out.append({
            "match_id": str(r["id"]),
            "match_type": r["match_type"],
            "matched_at": r["matched_at"],
            "other_profile_id": str(other_id),
            "other_display_name": other_name,
            "conversation_id": str(r["conversation_id"]) if r["conversation_id"] else None
        })
    return out