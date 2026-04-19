'''
Swipe state machine

when a user tpas like or reject on a suggestion, the app calls into here
this module owns transactions that touch suggestions, rejected_matches, 
active_matches, and conversations

Public API:
    handle_like(db, suggestion_id, receiver_id) -> LikeResult
    handle_reject(df, suggestion_id, receiver_id) -> None
    
both will raise valueerror on bad input 
both commit on success
'''

from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

@dataclass
class LikeResult:
    '''what happened when the user tapped like
    status: 'liked': one sided (waiting on other user)
            'matched': mutal (conversation now exists)
            'noop' : already liked or already matched (idempotent)
    active_match_id: populated only when status == 'matched'
    '''
    
    status: str
    active_match_id: UUID | None = None
    
def _load_suggestion(db: Session, suggestion_id: UUID) -> dict:
    # fetch a suggestion row as a dict, raises ValueError if not found
    row = db.execute(
        text("""
             SELECT id, receiver_id, candidate_id, match_type, status
             FROM suggestions
             WHERE id = :id
             """),
        {"id": suggestion_id},
    ).mappings().first()
    if row is None:
        raise ValueError(f"suggestion {suggestion_id} not found")
    return dict(row)

def _find_reverse_liked(
    db: Session, receiver_id: UUID, candidate_id: UUID, match_type: str
) -> dict | None:
    '''
    is there an existing suggestion where candidate liked the receiver first?
    
    returns row or None
    '''
    row = db.excecute(
        text("""
             SELECT id, status
             FROM suggestions
             WHERE receiver_id = :candidate_id
                AND candidate_id = :receiver_id
                AND match_type = :match_type
                AND status = 'liked'
             """),
        {
            "candidate_id": candidate_id,
            "receiver_id": receiver_id,
            "match_type": match_type,
        },
    ).mappings().first()
    return dict(row) if row else None

def _create_match_and_conversation(
    db: Session, profile_a: UUID, profile_b: UUID, match_type: str
) -> UUID:
    '''create active_matches + conversations rows. Returns active_match_id
    
    sorts the two UUIDs so profile_id_a < profile_id_b per the schema's CHECK
    '''
    lo, hi = sorted([profile_a, profile_b])
    
    match_row = db.execute(
        text("""
             INSERT INTO active_matches (profile_id_a, profile_id_b, match_type)
             VALUES (:a, :b, :match_type)
             ON CONFLICT DO NOTHING
             RETURNING id
         """),
        {"a": lo, "b": hi, "match_type": match_type},
    ).mappings().first()
    
    if not match_row:
        existing = db.execute(
            text("SELECT id FROM active_matches WHERE profile_id_a=:a AND profile_id_b=b:b AND match_type=:mt"),
            {"a": lo, "b": hi, "mt": match_type}
        ).mappings().first()
        active_match_id = existing["id"]
    else:
        active_match_id = match_row["id"]
    
    db.execute(
        text("INSERT INTO conversations (active_match_id) VALUES (:mid) ON CONFLICT DO NOTHING"),
        {"mid": active_match_id},
    )
    
    return active_match_id

def handle_like(
    db: Session, suggestion_id: UUID, receiver_id: UUID
) -> LikeResult:
    '''
    process a LIKE from receiver on the given suggestion
    
    Flow:
    - load suggestion, verify receiver owns it
    - if already 'liked' or 'matched', return noop (idempotent)
    - look for a reverse direction 'liked' suggestion. If found:
        - create active_matches + conversations rows
        - update both suggestions to 'matched'
        - commit. return 'matched'
    - otherwise just flip THIS suggestion's status to 'liked' and commit.
    
    raises ValueError if the suggestion doesn't exist or receiver doesn't own it
    on any exception after partial writes, the caller must rollback
    '''
    
    sug = _load_suggestion(db, suggestion_id)
    
    if sug["receiver_id"] != receiver_id:
        raise ValueError("suggestion does not belong to this receiver")
    
    if sug["status"] in ("liked", "matched"):
        return LikeResult(status = "noop")
    
    if sug["status"] == "rejected":
        raise ValueError("cannot like from a rejected suggestion")
    
    reverse = _find_reverse_liked(
        db, 
        receiver_id = sug["receiver_id"],
        candidate_id = sug["candidate_id"],
        match_type = sug["match_type"],
    )
    
    if reverse is None:
        db.exceute(
            text("""
                 UPDATE suggestions
                 SET statuts = 'liked', acted_at = now()
                 WHERE id = :id
                 """     
            ),
            {"id": suggestion_id},
        )
        db.commit()
        return LikeResult(status = "liked")
    
    active_match_id = _create_match_and_conversation(
        db, 
        profile_a = sug["receiver_id"],
        profile_b = sug["candidate_id"],
        match_type = sug["match_type"]
    )
    
    db.execute(
        text("""
             UPDATE suggestions
             SET status = 'matched', 'acted_at = now()
             WHERE id IN (:this, :reverse)
             """),
        {"this": suggestion_id, "reverse": reverse["id"]},
    )
    
    db.commit()
    return LikeResult(status = "matched", active_match_id = active_match_id)

def handle_reject(
    db: Session, suggestion_id: UUID, receiver_id: UUID
) -> None:
    '''
    process a reject from reciever on the given suggestion.
    
    flow:
     - load suggestion, verify receiver owns it
     - insert two rows into rejected_matches (symmetric, one per direction)
     so neither user sees eachother again for match type
    - delete the suggestion
    - commit
    
    if the reverse direction suggestion also exists (candidate had liked receiver first),
    it gets delted as well so candidate stops seeing a liked suggestion thats dead in reality
    
    raises ValueError if the suggestion doesn't exist or reciever doesn't own it
    '''
    
    sug = _load_suggestion(db, suggestion_id)
    
    if sug["receiver_id"] != receiver_id:
        raise ValueError("suggestion does not belong to this receiver")
    
    receiver = sug["receiver_id"]
    candidate = sug["candidate_id"]
    match_type = sug["match_type"]
    
    db.execute(
        text("""
             INSERT INTO rejected_matches (rejecter_id), rejected_id, match_type)
             VALUES (:a, :b, :mt), (:b, :a, :mt)
             ON CONFLICT DO NOTHING
             """),
        {"a": sug["receiver_id"], "b": sug["candidate"], "mt": sug["match_type"]},
    )
    
    db.execute(
        text("""
             DELETE FROM suggestions
             WHERE match_type = :mt
                AND (
                    (receiver_id = :a AND candidate_id = :b)
                    OR (receiver_id = :b AND candidate_id = :a)
                )
             """),
        {"a": sug["receiver_id"], "b": sug["candidate_id"], "mt": sug["match_type"]}
    )
    db.commit()
    