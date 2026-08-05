from flask_marshmallow import Marshmallow
from flask import Blueprint, current_app, g, jsonify, request
from extensions import db
from sqlalchemy import inspect, Column, Integer, String, DateTime, Boolean, Text, insert
from datetime import datetime, timedelta
from time import perf_counter
from urllib.parse import urlsplit
from sqlalchemy.exc import SQLAlchemyError
from utils.db_session import get_db_session 
ma = Marshmallow()

logs = Blueprint('logs', __name__)

class Logs(db.Model):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    userCuenta = Column(String(120)) 
    accountCuenta = Column(String(120))    
    fecha_log = Column(DateTime)  # ✅ Corrección en el tipo de dato
    ip = Column(String(120))   
    funcion = Column(String(120))   
    archivo = Column(String(120))   
    linea = Column(Integer) 
    error = Column(String(120))   
    codigoPostal = Column(String(120))
    latitude = Column(String(120))
    longitude = Column(String(120))
    language = Column(String(50))
    path = Column(String(500))
    method = Column(String(20))
    user_agent = Column(Text)
    referer = Column(String(1000))
    es_bot = Column(Boolean)
    status_code = Column(Integer)
    request_type = Column(String(50))
    trafico_sospechoso = Column(Boolean)
    motivo_sospecha = Column(String(50))
    duracion_ms = Column(Integer)
    
    def __init__(self, user_id=None, userCuenta=None, accountCuenta=None, fecha_log=None, ip=None,
                 funcion=None, archivo=None, linea=None, error=None, codigoPostal=None,
                 latitude=None, longitude=None, language=None, path=None, method=None,
                 user_agent=None, referer=None, es_bot=None, status_code=None,
                 request_type=None, trafico_sospechoso=None, motivo_sospecha=None, duracion_ms=None):
        self.user_id = user_id
        self.userCuenta = userCuenta
        self.accountCuenta = accountCuenta
        self.fecha_log = fecha_log
        self.ip = ip
        self.funcion = funcion
        self.archivo = archivo
        self.linea = linea
        self.error = error
        self.codigoPostal = codigoPostal
        self.latitude = latitude
        self.longitude = longitude
        self.language = language
        self.path = path
        self.method = method
        self.user_agent = user_agent
        self.referer = referer
        self.es_bot = es_bot
        self.status_code = status_code
        self.request_type = request_type
        self.trafico_sospechoso = trafico_sospechoso
        self.motivo_sospecha = motivo_sospecha
        self.duracion_ms = duracion_ms
    
    @classmethod
    def crear_tabla_logs(cls):
        insp = inspect(db.engine)
        if not insp.has_table("logs"):
            db.create_all()
        else:
            # Add motivo_sospecha column if missing (backward-compatible migration)
            try:
                existing_cols = [c['name'] for c in insp.get_columns('logs')]
                if 'motivo_sospecha' not in existing_cols:
                    db.engine.execute('ALTER TABLE logs ADD COLUMN motivo_sospecha VARCHAR(255)')
            except Exception:
                pass  # Non-critical: column may already exist or DB may not support this syntax

    @classmethod
    def eliminar_logs_antiguos(cls, dias):
        """Elimina logs de ingreso que sean más viejos que 'dias' días."""
        fecha_limite = datetime.now() - timedelta(days=dias)

        try:
            with get_db_session() as session:
                logs_antiguos = session.query(cls).filter(cls.fecha_log < fecha_limite).all()

                if logs_antiguos:  # Solo eliminar si hay registros
                    for log in logs_antiguos:
                        session.delete(log)
                    
                    session.commit()
                    print(f"{len(logs_antiguos)} logs eliminados con éxito.")

        except SQLAlchemyError as e:
          
            print(f"Error eliminando logs antiguos: {e}")

       

class MerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Logs
        load_instance = True
        sqla_session = db.session

mer_schema = MerSchema()
mer_schema_many = MerSchema(many=True)  # ✅ Nombre corregido


_BOT_MARKERS = (
    "bot", "crawler", "spider", "slurp", "headless",
    "facebookexternalhit", "whatsapp", "telegrambot", "bingpreview",
    "scanner", "zgrab", "masscan", "nmap", "nikto", "sqlmap",
)
_SUSPICIOUS_PATH_MARKERS = (
    "/.env", "/.git", "wp-admin", "wp-login", "phpmyadmin", "../",
)


def _client_ip():
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip[:120]
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",", 1)[0].strip() or request.remote_addr or "")[:120]


def _request_type():
    if request.path.startswith("/api/"):
        return "api"
    if request.method != "GET":
        return "action"
    return "page"


def _is_bot(user_agent):
    normalized = (user_agent or "").lower()
    return any(marker in normalized for marker in _BOT_MARKERS)


def _suspicious_path(path):
    normalized = (path or "").lower()
    return any(marker in normalized for marker in _SUSPICIOUS_PATH_MARKERS)


def _resolved_page_endpoint(path):
    """Devuelve el endpoint GET real de una página o None si la ruta no existe."""
    clean_path = urlsplit(path or "").path
    if not clean_path.startswith("/"):
        return None
    try:
        endpoint, _ = current_app.url_map.bind_to_environ(request.environ).match(
            clean_path, method="GET"
        )
    except Exception:
        return None
    if endpoint == "static" or endpoint == "logs.browser_activity":
        return None
    return endpoint


def _safe_text(value, limit):
    if value is None:
        return None
    value = str(value).strip()
    return value[:limit] or None


@logs.route("/api/activity", methods=["POST"])
def browser_activity():
    """Recibe permanencia acumulada enviada por el navegador."""
    data = request.get_json(silent=True) or {}
    event = _safe_text(data.get("event"), 50)
    if event not in {"session_start", "heartbeat", "visibility", "page_exit"}:
        return jsonify({"error": "Evento de actividad inválido"}), 400

    try:
        duration_ms = max(0, min(int(data.get("duration_ms") or 0), 86_400_000))
    except (TypeError, ValueError):
        return jsonify({"error": "Duración inválida"}), 400

    user_agent = request.headers.get("User-Agent", "")
    page_path = _safe_text(data.get("path"), 500)
    page_endpoint = _resolved_page_endpoint(page_path)
    if _is_bot(user_agent) or _suspicious_path(page_path) or page_endpoint is None:
        return jsonify({"error": "Página de actividad inválida"}), 400

    values = {
        "user_id": None,
        "userCuenta": _safe_text(data.get("visitor_id"), 120),
        "accountCuenta": _safe_text(data.get("session_id"), 120),
        "fecha_log": datetime.utcnow(),
        "ip": _client_ip(),
        "funcion": "%s:%s" % (page_endpoint, event),
        "archivo": "activity-tracker.js",
        "linea": None,
        "error": None,
        "codigoPostal": _safe_text(data.get("postal_code"), 120),
        "latitude": _safe_text(data.get("latitude"), 120),
        "longitude": _safe_text(data.get("longitude"), 120),
        "language": _safe_text(data.get("language"), 50),
        "path": page_path,
        "method": request.method,
        "user_agent": user_agent or None,
        "referer": request.headers.get("Referer", "")[:1000] or None,
        "es_bot": False,
        "status_code": 200,
        "request_type": "browser_activity",
        "trafico_sospechoso": False,
        "motivo_sospecha": None,
        "duracion_ms": duration_ms,
    }
    try:
        with db.engine.begin() as connection:
            connection.execute(insert(Logs.__table__).values(**values))
    except Exception:
        current_app.logger.exception("No se pudo registrar la permanencia")
        return jsonify({"error": "No se pudo registrar la actividad"}), 500
    return jsonify({"ok": True}), 201

def init_request_logging(app):
    """Registra una fila por petición dinámica sin afectar su respuesta."""

    @app.before_request
    def _start_activity_timer():
        g.activity_started_at = perf_counter()

    @app.after_request
    def _save_activity_log(response):
        # Los recursos estáticos no representan navegación y generan demasiado ruido.
        if request.path.startswith("/static/") or request.endpoint == "logs.browser_activity":
            return response

        # Carga el rastreador en cualquier landing/página HTML servida por Flask.
        content_type = response.headers.get("Content-Type", "")
        if (
            request.method == "GET"
            and response.status_code == 200
            and "text/html" in content_type
            and not response.direct_passthrough
        ):
            html = response.get_data(as_text=True)
            tracker = '<script src="/static/js/activity-tracker.js" defer></script>'
            if tracker not in html and "</body>" in html.lower():
                closing_index = html.lower().rfind("</body>")
                response.set_data(html[:closing_index] + tracker + html[closing_index:])

        user_agent = request.headers.get("User-Agent", "")
        is_bot = _is_bot(user_agent)
        is_html_page = request.method == "GET" and "text/html" in content_type

        # Una página queda confirmada por /api/activity cuando ejecuta JavaScript.
        # Las demás peticiones solo se registran si Flask resolvió un endpoint real.
        if (
            request.url_rule is None
            or request.endpoint is None
            or request.method == "OPTIONS"
            or _suspicious_path(request.path)
            or is_bot
            or is_html_page
        ):
            return response

        started_at = getattr(g, "activity_started_at", perf_counter())
        values = {
            "fecha_log": datetime.utcnow(),
            "ip": _client_ip(),
            "funcion": (request.endpoint or "not_found")[:120],
            "archivo": (request.blueprint or "app")[:120],
            "error": str(response.status_code) if response.status_code >= 400 else None,
            "language": request.headers.get("Accept-Language", "")[:50] or None,
            "path": request.full_path.rstrip("?")[:500],
            "method": request.method[:20],
            "user_agent": user_agent or None,
            "referer": request.headers.get("Referer", "")[:1000] or None,
            "es_bot": is_bot,
            "status_code": response.status_code,
            "request_type": _request_type(),
            "trafico_sospechoso": False,
            "motivo_sospecha": None,
            "duracion_ms": max(0, round((perf_counter() - started_at) * 1000)),
        }
        try:
            # Transacción independiente: no altera commits/rollbacks de la vista.
            with db.engine.begin() as connection:
                connection.execute(insert(Logs.__table__).values(**values))
        except Exception:
            app.logger.exception("No se pudo registrar la actividad HTTP en logs")
        return response
