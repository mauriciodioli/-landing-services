"""Software landing integrated into the existing Flask application."""
import hashlib
import hmac
import secrets
import time
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from services.web_landing.models import Base, RateWindow
from services.web_landing.lead_service import InvalidLead, register, validate
from services.web_landing.content import CONTENT
from services.web_landing.privacy_content import PRIVACY

LANGUAGES = ('es', 'en', 'it')
PUBLIC_ORIGIN = 'https://web.dpia.site'
web_landing = Blueprint('web_landing', __name__)

def get_engine():
    # Reuse the existing persistence and credentials; create only this service's tables.
    if 'web_landing_engine' not in current_app.extensions:
        from extensions import db
        engine = db.engine
        Base.metadata.create_all(engine)
        current_app.extensions['web_landing_engine'] = engine
    return current_app.extensions['web_landing_engine']

@web_landing.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if response.mimetype in ('application/json', 'text/html'):
        response.headers['Cache-Control'] = 'no-store'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

@web_landing.get('/desarrollo-web')
def index():
    lang = request.accept_languages.best_match(LANGUAGES) or 'es'
    return redirect(url_for('web_landing.landing', lang=lang))

@web_landing.get('/desarrollo-web/<lang>/')
def landing(lang):
    if lang not in LANGUAGES:
        abort(404)
    if 'web_csrf' not in session:
        session['web_csrf'] = secrets.token_urlsafe(32)
    return render_template('web/index.html', c=CONTENT[lang], lang=lang, csrf_token=session['web_csrf'])

@web_landing.get('/desarrollo-web/<lang>/privacy/')
def privacy(lang):
    if lang not in LANGUAGES:
        abort(404)
    return render_template('web/privacy.html', lang=lang, p=PRIVACY[lang])

@web_landing.get('/desarrollo-web/health')
def health():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(select(1))
    except SQLAlchemyError:
        return jsonify(ok=False), 503
    return jsonify(ok=True)

@web_landing.get('/desarrollo-web/robots.txt')
def robots():
    return current_app.response_class('User-agent: *\nAllow: /\nDisallow: /desarrollo-web/api/\nSitemap: '+PUBLIC_ORIGIN+'/desarrollo-web/sitemap.xml\n', mimetype='text/plain')

@web_landing.get('/desarrollo-web/sitemap.xml')
def sitemap():
    entries = ''.join(f'<url><loc>{PUBLIC_ORIGIN}/desarrollo-web/{lang}/</loc>'+''.join(f'<xhtml:link rel="alternate" hreflang="{other}" href="{PUBLIC_ORIGIN}/desarrollo-web/{other}/"/>' for other in LANGUAGES)+'</url>' for lang in LANGUAGES)
    return current_app.response_class('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+entries+'</urlset>', mimetype='application/xml')

@web_landing.post('/desarrollo-web/api/leads')
def leads():
    if request.content_length is not None and request.content_length > 32 * 1024:
        return jsonify(ok=False, error='payload_too_large'), 413
    if request.headers.get('Origin') not in (None, request.host_url.rstrip('/'), 'https://' + request.host):
        return jsonify(ok=False, error='invalid_origin'), 403
    if not request.is_json:
        return jsonify(ok=False, error='invalid_fields'), 400
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, error='invalid_fields'), 400
    supplied = payload.get('csrf_token')
    if not isinstance(supplied, str) or not session.get('web_csrf') or not hmac.compare_digest(supplied, session['web_csrf']):
        return jsonify(ok=False, error='invalid_csrf'), 403
    if payload.get('website'):
        return jsonify(ok=False, error='invalid_fields'), 400
    try:
        engine = get_engine()
        # Atomic shared rate limit, including across Gunicorn workers.
        now = int(time.time())
        key = hmac.new(current_app.secret_key.encode(), f'{request.remote_addr}:{now // 3600}'.encode(), hashlib.sha256).hexdigest()
        with engine.begin() as conn:
            conn.execute(delete(RateWindow).where(RateWindow.expires_at < now))
            # SQLite and PostgreSQL use their native atomic UPSERT.
            if engine.dialect.name == 'sqlite':
                from sqlalchemy.dialects.sqlite import insert
            elif engine.dialect.name == 'postgresql':
                from sqlalchemy.dialects.postgresql import insert
            elif engine.dialect.name in ('mysql', 'mariadb'):
                from sqlalchemy.dialects.mysql import insert
            else:
                raise RuntimeError('Unsupported database dialect.')
            stmt = insert(RateWindow).values(key=key, count=1, expires_at=now+3600)
            if engine.dialect.name in ('mysql', 'mariadb'):
                conn.execute(stmt.on_duplicate_key_update(count=RateWindow.count+1))
            else:
                conn.execute(stmt.on_conflict_do_update(index_elements=['key'], set_={'count': RateWindow.count+1}))
            count = conn.execute(select(RateWindow.count).where(RateWindow.key == key)).scalar_one()
        if count > 15:
            response = jsonify(ok=False, error='rate_limited')
            response.headers['Retry-After'] = str(3600-now % 3600)
            return response, 429
        values = validate(payload)
        reference = register(engine, values)
    except InvalidLead as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except SQLAlchemyError:
        # Do not log request bodies, SQL parameters or personal information.
        current_app.logger.error('Unable to persist a web enquiry.')
        return jsonify(ok=False, error='storage_unavailable'), 503
    return jsonify(ok=True, reference=reference), 201

@web_landing.errorhandler(413)
def too_large(_):
    return jsonify(ok=False, error='payload_too_large'), 413
