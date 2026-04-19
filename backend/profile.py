from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas

def upsert_profile(account: models.Account, body: schemas.ProfileSetupRequest, db: Session) -> models.Profile:
    profile = db.query(models.Profile).filter(models.Profile.profile_id == account.profile_id).first()
    if not profile:
        profile = models.Profile(profile_id=account.profile_id)
        db.add(profile)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(profile_id, db: Session) -> models.Profile:
    profile = db.query(models.Profile).filter(models.Profile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile