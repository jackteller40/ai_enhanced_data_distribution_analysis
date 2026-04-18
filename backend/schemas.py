from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid


# --- Auth request bodies ---
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    university: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# --- Auth response shapes ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountResponse(BaseModel):
    profile_id: uuid.UUID
    email: str
    university: str
    verified: bool

    class Config:
        from_attributes = True


# --- Profile request bodies ---
class ProfileSetupRequest(BaseModel):
    display_name: str
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    bio: Optional[str] = None
    favorite_bar: Optional[str] = None
    likes_going_out: Optional[bool] = None
    smokes: Optional[bool] = None
    clubs: List[str] = []
    looking_for: List[str] = []


# --- Profile response shapes ---
class ProfileResponse(BaseModel):
    profile_id: uuid.UUID
    display_name: str
    major: Optional[str]
    graduation_year: Optional[int]
    bio: Optional[str]
    favorite_bar: Optional[str]
    likes_going_out: Optional[bool]
    smokes: Optional[bool]
    clubs: List[str]
    looking_for: List[str]
    status: str

    class Config:
        from_attributes = True