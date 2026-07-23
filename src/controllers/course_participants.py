import os
import smtplib
import hmac
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from sqlalchemy import or_

from models.course_participant import CourseParticipant
from utils.db_session import get_db_session

participants = Blueprint("participants", __name__)

COURSES = {
    "ia-marketing": "IA y sistemas automáticos",
    "ia-processes": "IA para procesos y decisiones",
    "masterclass-ia": "Del mundo físico a la IA",
}

EDITABLE_FIELDS = {
    "name",
    "email",
    "phone",
    "profile",
    "company",
    "job_title",
    "country",
    "city",
    "language",
    "course_date",
    "course_timezone",
    "status",
    "attendance_status",
    "notes",
}


def _utcnow():
    return datetime.utcnow()


def _parse_datetime(value):
    if not value:
        return None
    normalized = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _client_ip():
    # Nginx sets X-Real-IP from the socket peer, avoiding spoofed client headers.
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip[:45]
    forwarded = request.headers.get("X-Forwarded-For", "")
    proxy_peer = forwarded.rsplit(",", 1)[-1].strip()
    return (proxy_peer or request.remote_addr or "")[:45]


def _admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = os.getenv("PARTICIPANTS_ADMIN_TOKEN", "")
        supplied = request.headers.get("X-Admin-Token", "")
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            supplied = authorization[7:].strip()
        if not expected:
            return jsonify({"error": "PARTICIPANTS_ADMIN_TOKEN no está configurado"}), 503
        if not hmac.compare_digest(supplied, expected):
            return jsonify({"error": "No autorizado"}), 401
        return view(*args, **kwargs)

    return wrapped


def _mail_settings():
    return {
        "host": os.getenv("MAIL_SERVER", ""),
        "port": int(os.getenv("MAIL_PORT", "587")),
        "username": os.getenv("MAIL_USERNAME", ""),
        "password": os.getenv("MAIL_PASSWORD", ""),
        "sender": os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME", "")),
        "use_tls": os.getenv("MAIL_USE_TLS", "false").lower() in {"1", "true", "yes"},
        "use_ssl": os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes"},
    }


def _send_email(participant, kind):
    settings = _mail_settings()
    if not settings["host"] or not settings["sender"]:
        return False, "SMTP no configurado"

    date_text = "Fecha a confirmar"
    if participant.course_date:
        try:
            course_zone = ZoneInfo(participant.course_timezone)
            course_date = participant.course_date.replace(tzinfo=timezone.utc)
            date_text = course_date.astimezone(course_zone).strftime("%d/%m/%Y %H:%M")
        except (ValueError, KeyError):
            date_text = participant.course_date.strftime("%d/%m/%Y %H:%M UTC")

    if kind == "confirmation":
        subject = f"Inscripción recibida · {participant.course_title}"
        heading = "Tu inscripción fue recibida"
        introduction = "Gracias por registrarte. Guardamos correctamente tu lugar."
    else:
        subject = f"Recordatorio · {participant.course_title}"
        heading = "Tu curso se aproxima"
        introduction = "Te recordamos que falta poco para el curso en el que te registraste."

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = participant.email
    message.set_content(
        f"{heading}\n\n"
        f"Hola {participant.name},\n\n"
        f"{introduction}\n\n"
        f"Curso: {participant.course_title}\n"
        f"Fecha: {date_text}\n"
        f"Zona horaria: {participant.course_timezone}\n\n"
        "DPIA Solutions"
    )

    with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as smtp:
        if settings["use_tls"]:
            smtp.starttls()
        if settings["username"]:
            smtp.login(settings["username"], settings["password"])
        smtp.send_message(message)

    now = _utcnow()
    if kind == "confirmation":
        participant.confirmation_sent_at = now
    else:
        participant.reminder_sent_at = now
    return True, "Correo enviado"


def _get_participant(session, participant_id):
    participant = session.get(CourseParticipant, participant_id)
    if participant is None:
        abort(404)
    return participant


@participants.get("/admin/participantes")
def participants_page():
    return render_template("participants/index.html")


@participants.post("/api/course-participants")
def create_participant():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    course_slug = str(data.get("course_slug", "")).strip()
    consent = data.get("consent") is True

    if len(name) < 2:
        return jsonify({"error": "Nombre inválido"}), 400
    if "@" not in email or len(email) > 254:
        return jsonify({"error": "Correo electrónico inválido"}), 400
    if course_slug not in COURSES:
        return jsonify({"error": "Curso inválido"}), 400
    if not consent:
        return jsonify({"error": "Debes aceptar el consentimiento"}), 400

    try:
        course_date_value = data.get("course_date") or os.getenv(
            f"COURSE_DATE_{course_slug.upper().replace('-', '_')}",
            "",
        )
        course_date = _parse_datetime(course_date_value)
    except ValueError:
        return jsonify({"error": "Fecha del curso inválida"}), 400

    with get_db_session() as session:
        duplicate_query = session.query(CourseParticipant).filter_by(
            email=email,
            course_slug=course_slug,
            status="registered",
        )
        if course_date:
            duplicate_query = duplicate_query.filter(
                CourseParticipant.course_date == course_date
            )
        else:
            duplicate_query = duplicate_query.filter(
                CourseParticipant.course_date.is_(None)
            )
        existing = duplicate_query.first()
        if existing:
            return jsonify(
                {
                    "message": "Ya estabas registrado para este curso.",
                    "participant_id": existing.id,
                }
            ), 200

        participant = CourseParticipant(
            course_slug=course_slug,
            course_title=COURSES[course_slug],
            course_date=course_date,
            course_timezone=str(
                data.get("course_timezone")
                or os.getenv("COURSE_TIMEZONE", "Europe/Rome")
            )[:64],
            name=name[:160],
            email=email,
            phone=str(data.get("phone") or "").strip()[:60] or None,
            profile=str(data.get("profile") or "").strip()[:80] or None,
            company=str(data.get("company") or "").strip()[:180] or None,
            job_title=str(data.get("job_title") or "").strip()[:160] or None,
            country=str(data.get("country") or "").strip()[:100] or None,
            city=str(data.get("city") or "").strip()[:120] or None,
            language=str(data.get("language") or "")[:12] or None,
            consent=True,
            consent_at=_utcnow(),
            source=str(data.get("source") or "")[:100] or None,
            page_url=str(data.get("page_url") or "")[:2000] or None,
            referrer=str(data.get("referrer") or "")[:2000] or None,
            utm_source=str(data.get("utm_source") or "")[:160] or None,
            utm_medium=str(data.get("utm_medium") or "")[:160] or None,
            utm_campaign=str(data.get("utm_campaign") or "")[:160] or None,
            utm_term=str(data.get("utm_term") or "")[:160] or None,
            utm_content=str(data.get("utm_content") or "")[:160] or None,
            ip_address=_client_ip(),
            user_agent=request.headers.get("User-Agent", "")[:1000] or None,
            browser_language=str(data.get("browser_language") or "")[:64] or None,
            screen_resolution=str(data.get("screen_resolution") or "")[:32] or None,
        )
        session.add(participant)
        session.flush()
        participant_id = participant.id

    confirmation_sent = False
    try:
        with get_db_session() as session:
            participant = _get_participant(session, participant_id)
            confirmation_sent, _ = _send_email(participant, "confirmation")
    except Exception:
        current_app.logger.exception("No se pudo enviar la confirmación")

    return jsonify(
        {
            "message": "Registro guardado correctamente.",
            "participant_id": participant_id,
            "confirmation_sent": confirmation_sent,
        }
    ), 201


@participants.get("/api/course-participants")
@_admin_required
def list_participants():
    search = request.args.get("q", "").strip()
    course = request.args.get("course", "").strip()
    status = request.args.get("status", "").strip()
    with get_db_session() as session:
        query = session.query(CourseParticipant)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    CourseParticipant.name.ilike(pattern),
                    CourseParticipant.email.ilike(pattern),
                    CourseParticipant.phone.ilike(pattern),
                    CourseParticipant.company.ilike(pattern),
                )
            )
        if course:
            query = query.filter_by(course_slug=course)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(CourseParticipant.registered_at.desc()).all()
        payload = [row.to_dict() for row in rows]
    return jsonify({"participants": payload})


@participants.get("/api/course-participants/<int:participant_id>")
@_admin_required
def get_participant(participant_id):
    with get_db_session() as session:
        payload = _get_participant(session, participant_id).to_dict()
    return jsonify(payload)


@participants.patch("/api/course-participants/<int:participant_id>")
@_admin_required
def update_participant(participant_id):
    data = request.get_json(silent=True) or {}
    with get_db_session() as session:
        row = _get_participant(session, participant_id)
        for field in EDITABLE_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if field == "course_date":
                value = _parse_datetime(value)
            elif isinstance(value, str):
                value = value.strip() or None
            setattr(row, field, value)
        session.flush()
        payload = row.to_dict()
    return jsonify(payload)


@participants.delete("/api/course-participants/<int:participant_id>")
@_admin_required
def delete_participant(participant_id):
    with get_db_session() as session:
        session.delete(_get_participant(session, participant_id))
    return jsonify({"message": "Participante eliminado"})


@participants.post("/api/course-participants/<int:participant_id>/confirmation")
@_admin_required
def send_confirmation(participant_id):
    try:
        with get_db_session() as session:
            row = _get_participant(session, participant_id)
            sent, message = _send_email(row, "confirmation")
    except Exception as exc:
        current_app.logger.exception("Error enviando confirmación")
        return jsonify({"error": str(exc)}), 502
    return jsonify({"sent": sent, "message": message}), 200 if sent else 503


@participants.post("/api/course-participants/<int:participant_id>/reminder")
@_admin_required
def send_reminder(participant_id):
    try:
        with get_db_session() as session:
            row = _get_participant(session, participant_id)
            sent, message = _send_email(row, "reminder")
    except Exception as exc:
        current_app.logger.exception("Error enviando recordatorio")
        return jsonify({"error": str(exc)}), 502
    return jsonify({"sent": sent, "message": message}), 200 if sent else 503


@participants.post("/api/course-participants/reminders/run")
@_admin_required
def run_due_reminders():
    days_before = int(os.getenv("COURSE_REMINDER_DAYS", "2"))
    now = _utcnow()
    deadline = now + timedelta(days=days_before)
    sent = 0
    errors = []
    with get_db_session() as session:
        due = session.query(CourseParticipant).filter(
            CourseParticipant.status == "registered",
            CourseParticipant.course_date.isnot(None),
            CourseParticipant.course_date >= now,
            CourseParticipant.course_date <= deadline,
            CourseParticipant.reminder_sent_at.is_(None),
        ).all()
        due_count = len(due)
        for row in due:
            try:
                ok, message = _send_email(row, "reminder")
                if ok:
                    sent += 1
                else:
                    errors.append({"id": row.id, "error": message})
            except Exception as exc:
                current_app.logger.exception("Error enviando recordatorio automático")
                errors.append({"id": row.id, "error": str(exc)})
    return jsonify({"due": due_count, "sent": sent, "errors": errors})
