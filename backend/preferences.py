from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import models, schemas

def upsert_romantic_preferences(
    account: models.Account,
    body: schemas.RomanticPreferencesRequest,
    db: Session
) -> models.RomanticPreference:
    prefs = db.query(models.RomanticPreference).filter(
        models.RomanticPreference.profile_id == account.profile_id
    ).first()
    if not prefs: 
        prefs = models.RomanticPreference(profile_id = account.profile_id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_unset = True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs

def upsert_roommate_preferences(
    account: models.Account,
    body: schemas.RoommatePreferencesRequest,
    db: Session
) -> models.RoommatePreference:
    prefs = db.query(models.RoommatePreference).filter(
        models.RoommatePreference.profile_id == account.profile_id
    ).first()
    if not prefs: 
        prefs = models.RoommatePreference(profile_id = account.profile_id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_unset = True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs
    