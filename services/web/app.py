"""Independent commercial application. No imports from the existing DPIA app."""
import hashlib
import hmac
import os
import secrets
import time
from datetime import timedelta
from pathlib import Path
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix
from models import Base, RateWindow
from lead_service import InvalidLead, register, validate
from content import CONTENT
from privacy_content import PRIVACY

LANGUAGES = ('es', 'en', 'it')
PUBLIC_ORIGIN = 'https://web.dpia.site'

def create_app(test_config=None):
    app = Flask(__name__)
    secret = os.environ.get('SECRET_KEY')
    testing = bool(test_config and test_config.get('TESTING'))
    if not secret and not testing:
        raise RuntimeError('Set SECRET_KEY to a random secret before starting this service.')
    if secret and len(secret) < 32 and not testing:
        raise RuntimeError('SECRET_KEY must contain at least 32 characters.')
    app.config.from_mapping(
        SECRET_KEY=secret or 'test-only-secret',
        PUBLIC_HOST=os.environ.get('PUBLIC_HOST', 'web.dpia.site'),
        DATABASE_URL=os.environ.get('DATABASE_URL', 'sqlite:////data/leads.sqlite'),
        MAX_CONTENT_LENGTH=32 * 1024,
        SESSION_COOKIE_NAME='dpia_web_session',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    )
    if test_config:
        app.config.update(test_config)
    # Only accessible via loopback behind exactly one local Nginx proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    if os.environ.get('APP_ENV') == 'development' and app.config['PUBLIC_HOST'] in ('localhost', '127.0.0.1'):
        app.config['SESSION_COOKIE_SECURE'] = False
    database_url = app.config['DATABASE_URL']
    if database_url.startswith('sqlite:///') and database_url != 'sqlite:///:memory:':
        Path(database_url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={'timeout': 15} if database_url.startswith('sqlite') else {})
    if database_url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_settings(connection, _):
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('PRAGMA busy_timeout=15000')
    Base.metadata.create_all(engine)
    app.extensions['web_engine'] = engine

    @app.before_request
    def restrict_host():
        # Reject foreign hosts rather than serving the new landing under dpia.site.
        if request.host.split(':', 1)[0].lower() != app.config['PUBLIC_HOST']:
            abort(404)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/') or response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-store'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get('/')
    def index():
        lang = request.accept_languages.best_match(LANGUAGES) or 'es'
        return redirect(url_for('landing', lang=lang))

    @app.get('/<lang>/')
    def landing(lang):
        if lang not in LANGUAGES:
            abort(404)
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        session.permanent = True
        return render_template('index.html', c=CONTENT[lang], lang=lang, csrf_token=session['csrf'])

    @app.get('/<lang>/privacy/')
    def privacy(lang):
        if lang not in LANGUAGES:
            abort(404)
        return render_template('privacy.html', lang=lang, p=PRIVACY[lang])

    @app.get('/health')
    def health():
        try:
            with engine.connect() as conn:
                conn.execute(select(1))
        except SQLAlchemyError:
            return jsonify(ok=False), 503
        return jsonify(ok=True)

    @app.get('/robots.txt')
    def robots():
        return app.response_class('User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: '+PUBLIC_ORIGIN+'/sitemap.xml\n', mimetype='text/plain')

    @app.get('/sitemap.xml')
    def sitemap():
        entries = ''.join(f'<url><loc>{PUBLIC_ORIGIN}/{lang}/</loc>'+''.join(f'<xhtml:link rel="alternate" hreflang="{other}" href="{PUBLIC_ORIGIN}/{other}/"/>' for other in LANGUAGES)+'</url>' for lang in LANGUAGES)
        return app.response_class('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'+entries+'</urlset>', mimetype='application/xml')

    @app.post('/api/leads')
    def leads():
        if request.headers.get('Origin') not in (None, PUBLIC_ORIGIN):
            return jsonify(ok=False, error='invalid_origin'), 403
        if not request.is_json:
            return jsonify(ok=False, error='invalid_fields'), 400
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(ok=False, error='invalid_fields'), 400
        supplied = payload.get('csrf_token')
        if not isinstance(supplied, str) or not session.get('csrf') or not hmac.compare_digest(supplied, session['csrf']):
            return jsonify(ok=False, error='invalid_csrf'), 403
        if payload.get('website'):
            return jsonify(ok=False, error='invalid_fields'), 400
        try:
            # Atomic shared rate limit, including across Gunicorn workers.
            now = int(time.time())
            key = hmac.new(app.secret_key.encode(), f'{request.remote_addr}:{now // 3600}'.encode(), hashlib.sha256).hexdigest()
            with engine.begin() as conn:
                conn.execute(delete(RateWindow).where(RateWindow.expires_at < now))
                # SQLite and PostgreSQL use their native atomic UPSERT.
                if engine.dialect.name == 'sqlite':
                    from sqlalchemy.dialects.sqlite import insert
                elif engine.dialect.name == 'postgresql':
                    from sqlalchemy.dialects.postgresql import insert
                else:
                    raise RuntimeError('Rate limiter supports SQLite and PostgreSQL.')
                stmt = insert(RateWindow).values(key=key, count=1, expires_at=now+3600)
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
            app.logger.error('Unable to persist a web enquiry.')
            return jsonify(ok=False, error='storage_unavailable'), 503
        return jsonify(ok=True, reference=reference), 201

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(ok=False, error='payload_too_large'), 413

    return app
