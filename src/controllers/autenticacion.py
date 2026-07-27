from flask import Blueprint, request, jsonify, render_template, current_app
from utils.db_session import get_db_session

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

    # return token if present
    return jsonify({'ok': True, 'token': usuario.get('token'), 'role': usuario.get('roll')}), 200
