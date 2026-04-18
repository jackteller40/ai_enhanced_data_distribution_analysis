from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
import models, schemas, auth, profile, conversation

app = FastAPI(title="MatchApp API")


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

@app.post("/profile/setup", response_model=schemas.ProfileResponse, status_code=201)
def setup_profile(
    body: schemas.ProfileSetupRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return profile.create_profile(current_user, body, db)


@app.put("/profile", response_model=schemas.ProfileResponse)
def update_profile(
    body: schemas.ProfileSetupRequest,
    db: Session = Depends(get_db),
    current_user: models.Account = Depends(auth.get_current_user),
):
    return profile.update_profile(current_user, body, db)


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