"""Role-based access using the same user tokens as the existing administration."""
import base64
from functools import wraps
from flask import g, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.db_session import get_db_session

def lookup_token(token):
    with get_db_session() as session:
        row = session.execute(text('SELECT id, correo_electronico, activo, roll FROM usuarios WHERE token = :token LIMIT 1'), {'token': token}).mappings().first()
        return dict(row) if row else None

def lookup_basic(email, password):
    from controllers.campania_telefonica import _consultar_usuario_por_correo, _verificar_password_usuario
    user = _consultar_usuario_por_correo(email.lower())
    return user if user and _verificar_password_usuario(user.get('password'), password) else None

def require_admin_roles(*roles):
    allowed = {role.lower() for role in roles}
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get('Authorization', '')
            try:
                if authorization.lower().startswith('basic '):
                    try:
                        email, password = base64.b64decode(authorization.split(None, 1)[1], validate=True).decode('utf-8').split(':', 1)
                    except (ValueError, UnicodeError):
                        return jsonify(error='Credenciales inválidas'), 401
                    user = lookup_basic(email, password)
                else:
                    token = authorization[7:].strip() if authorization.lower().startswith('bearer ') else request.headers.get('X-Admin-Token', '').strip()
                    if not token:
                        return jsonify(error='Inicia sesión para continuar'), 401
                    user = lookup_token(token)
            except SQLAlchemyError:
                return jsonify(error='No se pudo verificar el acceso'), 503
            if not user:
                return jsonify(error='Credenciales inválidas'), 401
            if not user.get('activo') or str(user.get('roll', '')).strip().lower() not in allowed:
                return jsonify(error='Acceso reservado a administradores y moderadores'), 403
            g.admin_user = user
            return view(*args, **kwargs)
        return wrapped
    return decorate
