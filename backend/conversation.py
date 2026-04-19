from sqlalchemy.orm import Session
from fastapi import HTTPException
import models, schemas


def create_conversation(active_match_id, db: Session) -> models.Conversation:
    existing = db.query(models.Conversation).filter(models.Conversation.active_match_id == active_match_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Conversation already exists")

    conversation = models.Conversation(active_match_id=active_match_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def send_message(account: models.Account, conversation_id, body: schemas.SendMessageRequest, db: Session) -> models.Message:
    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    match = db.query(models.ActiveMatch).filter(models.ActiveMatch.id == conversation.active_match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.profile_id_a == account.profile_id:
        recipient_id = match.profile_id_b
    else:
        recipient_id = match.profile_id_a

    message = models.Message(
        conversation_id = conversation_id,
        sender_id       = account.profile_id,
        recipient_id    = recipient_id,
        content         = body.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages(conversation_id, db: Session) -> list[models.Message]:
    return db.query(models.Message)\
        .filter(models.Message.conversation_id == conversation_id)\
        .order_by(models.Message.sent_at)\
        .all()


def mark_read(account: models.Account, conversation_id, db: Session):
    db.query(models.Message)\
        .filter(
            models.Message.conversation_id == conversation_id,
            models.Message.sender_id != account.profile_id,
            models.Message.read == False,
        )\
        .update({"read": True})
    db.commit()