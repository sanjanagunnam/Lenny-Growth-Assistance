"""SQLAlchemy ORM models for conversational sessions and messages."""

from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class Session(Base):
    """Conversational session entity storing chat threads and artifacts."""

    __tablename__ = "sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
        doc="Unique UUID primary key",
    )
    title = Column(
        String(255),
        nullable=False,
        default="New Conversation",
        doc="Human-readable title or generated topic summary",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        doc="Timestamp when session was initiated",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        doc="Timestamp of latest message in this session",
    )

    # Relationship to messages
    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<Session(id='{self.id}', title='{self.title}')>"


class Message(Base):
    """Message entity representing user prompts, assistant answers, and system instructions."""

    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Serial primary key",
    )
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key referencing Session.id",
    )
    role = Column(
        String(50),
        nullable=False,
        doc="'user', 'assistant', or 'system'",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Markdown content of the message",
    )
    provider = Column(
        String(100),
        nullable=True,
        doc="Provider and model descriptor (e.g. 'ollama:llama3.2', 'anthropic:claude-3-5-sonnet-latest')",
    )
    sources = Column(
        Text,
        nullable=True,
        doc="JSON-encoded grounding sources and citations from RAG retrieval",
    )
    artifact_type = Column(
        String(100),
        nullable=True,
        doc="Type of structured artifact if generated (e.g. 'growth_experiment', 'lno_audit', 'strategy')",
    )
    artifact_content = Column(
        Text,
        nullable=True,
        doc="Raw text or JSON markdown of the generated artifact",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        doc="Message timestamp",
    )

    # Relationship back to session
    session = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id='{self.session_id}', role='{self.role}')>"
