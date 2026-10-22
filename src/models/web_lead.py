"""Web enquiries registered in the shared Flask-SQLAlchemy metadata."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db

class Lead(db.Model):
    __tablename__ = 'web_leads'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    language: Mapped[str] = mapped_column(String(2))
    business_type: Mapped[str] = mapped_column(String(30))
    solution_type: Mapped[str] = mapped_column(String(30))
    features: Mapped[str] = mapped_column(Text)
    online_payments: Mapped[str] = mapped_column(String(10))
    ai: Mapped[str] = mapped_column(String(10))
    integration: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    integration_details: Mapped[str] = mapped_column(Text, default='')
    privacy_version: Mapped[str] = mapped_column(String(20), default='2026-10-22')

class RateWindow(db.Model):
    __tablename__ = 'web_rate_windows'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
