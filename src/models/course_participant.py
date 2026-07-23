from datetime import datetime
from sqlalchemy import inspect

from extensions import db


class CourseParticipant(db.Model):
    __tablename__ = "course_participant"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    course_slug = db.Column(db.String(80), nullable=False, index=True)
    course_title = db.Column(db.String(180), nullable=False)
    course_date = db.Column(db.DateTime, nullable=True, index=True)
    course_timezone = db.Column(db.String(64), nullable=False, default="Europe/Rome")

    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), nullable=False, index=True)
    phone = db.Column(db.String(60), nullable=True)
    profile = db.Column(db.String(80), nullable=True)
    company = db.Column(db.String(180), nullable=True)
    job_title = db.Column(db.String(160), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    language = db.Column(db.String(12), nullable=True)

    consent = db.Column(db.Boolean, nullable=False, default=False)
    consent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="registered", index=True)
    attendance_status = db.Column(db.String(30), nullable=False, default="pending")
    notes = db.Column(db.Text, nullable=True)

    source = db.Column(db.String(100), nullable=True)
    page_url = db.Column(db.Text, nullable=True)
    referrer = db.Column(db.Text, nullable=True)
    utm_source = db.Column(db.String(160), nullable=True)
    utm_medium = db.Column(db.String(160), nullable=True)
    utm_campaign = db.Column(db.String(160), nullable=True)
    utm_term = db.Column(db.String(160), nullable=True)
    utm_content = db.Column(db.String(160), nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    browser_language = db.Column(db.String(64), nullable=True)
    screen_resolution = db.Column(db.String(32), nullable=True)

    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    confirmation_sent_at = db.Column(db.DateTime, nullable=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        def iso(value):
            return value.isoformat() if value else None

        return {
            "id": self.id,
            "course_slug": self.course_slug,
            "course_title": self.course_title,
            "course_date": iso(self.course_date),
            "course_timezone": self.course_timezone,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "profile": self.profile,
            "company": self.company,
            "job_title": self.job_title,
            "country": self.country,
            "city": self.city,
            "language": self.language,
            "consent": self.consent,
            "consent_at": iso(self.consent_at),
            "status": self.status,
            "attendance_status": self.attendance_status,
            "notes": self.notes,
            "source": self.source,
            "page_url": self.page_url,
            "referrer": self.referrer,
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_term": self.utm_term,
            "utm_content": self.utm_content,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "browser_language": self.browser_language,
            "screen_resolution": self.screen_resolution,
            "registered_at": iso(self.registered_at),
            "updated_at": iso(self.updated_at),
            "confirmation_sent_at": iso(self.confirmation_sent_at),
            "reminder_sent_at": iso(self.reminder_sent_at),
        }

    @classmethod
    def crear_tabla_si_no_existe(cls):
        insp = inspect(db.engine)
        if not insp.has_table(cls.__tablename__):
            db.create_all()