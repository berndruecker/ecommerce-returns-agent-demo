import logging
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from models import EmailNotification
from data_store import data_store

router = APIRouter()
logger = logging.getLogger("fake-services.notifications")

# ========== Send Email ==========
@router.post("/email", response_model=EmailNotification)
async def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: List[str] = None
):
    """Send email notification"""
    logger.info("Notifications send-email request: to=%s, subject=%s", to, subject)
    if not to or "@" not in to:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    email = EmailNotification(
        email_id=data_store.generate_id("EML"),
        to=to,
        subject=subject,
        body=body,
        attachments=attachments or [],
        sent_at=datetime.now()
    )
    
    data_store.email_notifications.append(email)
    logger.info("Notifications send-email response: email_id=%s, to=%s", email.email_id, email.to)
    return email
