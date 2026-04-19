from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime


# --- Auth request bodies ---
class SignupRequest(BaseModel):
    email: EmailStr
    password: str


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
    varsity_sports: List[str] = []
    interests: List[str] = []
    nicotine_lover: Optional[bool] = None
    height: Optional[int] = None
    gender: Optional[str] = None
    romantically_searching_for: Optional[str] = None


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
    nicotine_lover: Optional[bool]
    height: Optional[int]
    gender: Optional[str]
    clubs: List[str]
    varsity_sports: Optional[List[str]]
    interests: Optional[List[str]]
    looking_for: List[str]
    romantically_searching_for: Optional[str]
    status: str

    class Config:
        from_attributes = True

# --- Message Request shapes ---
class SendMessageRequest(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    content: str
    sent_at: datetime
    read: bool

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: uuid.UUID
    active_match_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
        
class RomanticPreferencesRequest(BaseModel):
    interested_in_genders: Optional[list[str]] = None
    min_grad_yr: Optional[int] = None
    max_grad_yr: Optional[int] = None
    min_preferred_height: Optional[int] = None
    max_preferred_height: Optional[int] = None
    priority_weights: Optional[dict] = None

class RoommatePreferencesRequest(BaseModel):
    roommate_gender_preference: Optional[str] = None
    sleep_schedule: Optional[str] = None
    cleanlieness: Optional[int] = None
    noise_tolerance: Optional[int] = None
    ok_with_pets: Optional[bool] = None
    guests_frequency: Optional[str] = None
    on_campus: Optional[bool] = None
    priority_weights: Optional[dict] = None
    
class RomanticPreferencesResponse(BaseModel):
    profile_id: uuid.UUID
    interested_in_genders: Optional[List[str]]
    min_grad_yr: Optional[int]
    max_grad_yr: Optional[int]
    min_preferred_height: Optional[int]
    max_preferred_height: Optional[int]
    priority_weights: Optional[dict]
    
    class Config:
        from_attributes = True
        
class RoommatePreferencesResponse(BaseModel):
    profile_id: uuid.UUID
    roommate_gender_preference: Optional[str]
    sleep_schedule: Optional[str]
    cleanliness: Optional[int]
    noise_tolerance: Optional[int]
    has_pets: Optional[bool]
    ok_with_pets: Optional[bool]
    guests_frequency: Optional[str]
    on_campus: Optional[bool]
    priority_weights: Optional[dict]
    
    class Config:
        from_attributes = True
        
class CandidateProfile(BaseModel):
    display_name: str
    graduation_year: Optional[int]
    major: Optional[str]
    bio: Optional[str]
    likes_going_out: Optional[bool]
    clubs: List[str]
    photos: List[str]

class SuggestionResponse(BaseModel):
    id: uuid.UUID
    match_score: float
    agent_explanation: Optional[str]
    candidate_profile: CandidateProfile

    class Config:
        from_attributes = True
    
class MatchResponse(BaseModel):
    match_id: uuid.UUID
    match_type: str
    matched_at: datetime
    other_profile_id: uuid.UUID
    other_display_name: str
    conversation_id: Optional[uuid.UUID]
    
class LikeResponse(BaseModel):
    status: str #liked/matched/noop
    active_match_id: Optional[uuid.UUID]