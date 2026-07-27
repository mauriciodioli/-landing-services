from flask import Blueprint, request, jsonify, render_template, current_app
from utils.db_session import get_db_session
from sqlalchemy import text
import secrets
from datetime import datetime, timedelta
# PyJWT is optional; import only when needed

autenticacion = Blueprint('autenticacion', __name__)


@autenticacion.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@autenticacion.route('/auth/login', methods=['POST'])
def login_api():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({'error': 'Credenciales inválidas'}), 400

    try:
        # reuse helpers from campania_telefonica for password verification
        from controllers.campania_telefonica import (
            _consultar_usuario_por_correo,
            _verificar_password_usuario,
        )
    except Exception:
        return jsonify({'error': 'Autenticación no disponible'}), 503

    usuario = _consultar_usuario_por_correo(email)
    if not usuario:
        return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
    if not bool(usuario.get('activo')):
        return jsonify({'error': 'Usuario inactivo'}), 403

    if not _verificar_password_usuario(usuario.get('password'), password):
        return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401

    # success — check role
    allowed = {'administrador', 'avanzado', 'moderador'}
    role = (usuario.get('roll') or '').lower()
    if role not in allowed:
        return jsonify({'error': 'Acceso restringido'}), 403

    # Build or persist a token for the user. Prefer JWT if app secret available.
    token_value = usuario.get('token')
    secret = current_app.config.get('JWT_SECRET_KEY') or None
    if not token_value:
        if secret:
            try:
                import jwt as _jwt
                # generate a JWT WITHOUT exp so it remains valid until explicit logout
                payload = {
                    'sub': int(usuario.get('id')),
                }
                token_value = _jwt.encode(payload, secret, algorithm='HS256')
                # PyJWT may return bytes on some versions
                if isinstance(token_value, bytes):
                    token_value = token_value.decode('utf-8')
            except Exception:
                current_app.logger.exception('PyJWT no disponible o error generando JWT; usando token aleatorio')
                token_value = secrets.token_urlsafe(32)
        else:
            token_value = secrets.token_urlsafe(32)

        # persist token in DB
        try:
            with get_db_session() as session:
                session.execute(
                    text("UPDATE usuarios SET token = :token WHERE id = :id"),
                    {"token": token_value, "id": int(usuario.get('id'))},
                )
        except Exception:
            # ignore persistence failures but still return token
            current_app.logger.exception('No se pudo guardar token de usuario')

    current_app.logger.info('LOGIN token_value for %s: %r', email, token_value)
    return jsonify({'ok': True, 'token': token_value, 'role': usuario.get('roll')}), 200



@autenticacion.route('/auth/logout', methods=['POST'])
def logout_api():
    # Accept token via Authorization header Bearer or JSON body {token:...}
    auth = (request.headers.get('Authorization') or '').strip()
    token = ''
    if auth.lower().startswith('bearer '):
        token = auth[7:].strip()
    else:
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or '').strip()

    if not token:
        return jsonify({'error': 'No token proporcionado'}), 400

    try:
        with get_db_session() as session:
            session.execute(
                text("UPDATE usuarios SET token = NULL WHERE token = :token"),
                {"token": token},
            )
    except Exception:
        current_app.logger.exception('Error borrando token')
        return jsonify({'error': 'Error borrando token'}), 500

    return jsonify({'ok': True}), 200
