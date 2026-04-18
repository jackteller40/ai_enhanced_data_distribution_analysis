from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas


def create_profile(account: models.Account, body: schemas.ProfileSetupRequest, db: Session) -> models.Profile:
    existing = db.query(models.Profile).filter(models.Profile.profile_id == account.profile_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")

    profile = models.Profile(
        profile_id      = account.profile_id,
        display_name    = body.display_name,
        major           = body.major,
        graduation_year = body.graduation_year,
        bio             = body.bio,
        favorite_bar    = body.favorite_bar,
        likes_going_out = body.likes_going_out,
        smokes          = body.smokes,
        clubs           = body.clubs,
        looking_for     = body.looking_for,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(account: models.Account, body: schemas.ProfileSetupRequest, db: Session) -> models.Profile:
    profile = db.query(models.Profile).filter(models.Profile.profile_id == account.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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