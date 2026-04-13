from sqlalchemy import Column, String, DateTime
from datetime import datetime
from server.database import Base

class UserInfo(Base):
    __tablename__ = "user_info"
    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    user_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    points_total = Column(String, default="0")
    points_balance = Column(String, default="0")
    subscription_info = Column(String, default="FREE")
    is_activated = Column(String, default="1")
    login_method = Column(String, default="email")
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    email = Column(String, primary_key=True, index=True)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class ConversationManagement(Base):
    __tablename__ = "conversation_management"
    conversation_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    conversation_name = Column(String, nullable=True)
    created_time = Column(DateTime, default=datetime.utcnow)
    updated_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    canvas = Column(String, nullable=True)
    messages = Column(String, nullable=True)

class InvitationCode(Base):
    __tablename__ = "invitation_codes"
    code = Column(String, primary_key=True, index=True)
    remaining_uses = Column(String, nullable=False, default="3")
    created_at = Column(DateTime, default=datetime.utcnow)