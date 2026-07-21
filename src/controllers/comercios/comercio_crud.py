from flask import Blueprint, request, jsonify, session
from datetime import datetime
from utils.db_session import get_db_session
from models.comercios.comercio import Comercio
from models.usuario import Usuario

comercio_crud = Blueprint('comercio_crud', __name__)


@comercio_crud.route('/api/comercio/register', methods=['POST'])
def api_comercio_register():
    """Alta simple de comercio. Requiere `email` (usuario existente) y `nombre` mínimo."""
    try:
        data = request.get_json() or {}
        nombre = data.get('nombre')
        email = data.get('email')
        telefono = data.get('telefono')
        direccion = data.get('direccion')
        lat = data.get('lat')
        lon = data.get('lon')
        ambito = data.get('ambito')
        categoria_id = data.get('categoria_id')

        if not nombre or not email:
            return jsonify({'success': False, 'message': 'Faltan campos requeridos: nombre o email'}), 400

        with get_db_session() as db_session:
            usuario = db_session.query(Usuario).filter_by(correo_electronico=email).first()
            if not usuario:
                return jsonify({'success': False, 'message': 'Usuario no encontrado para ese email'}), 404

            # Verificar si ya existe comercio para este usuario
            existe = db_session.query(Comercio).filter_by(user_id=usuario.id).first()
            if existe:
                return jsonify({'success': False, 'message': 'Ya existe un comercio para este usuario'}), 400

            nuevo = Comercio(
                user_id=usuario.id,
                nombre=nombre,
                telefono=telefono,
                email=email,
                direccion=direccion,
                latitud=lat,
                longitud=lon,
                ambito=ambito,
                categoria_id=categoria_id,
                activo=True,
                fecha_alta=datetime.now()
            )
            db_session.add(nuevo)
            db_session.flush()

            # Guardar en sesión como comercio logueado
            session['comercio_id'] = nuevo.id
            session['comercio_nombre'] = nuevo.nombre

            return jsonify({'success': True, 'message': 'Comercio creado', 'comercio': {'id': nuevo.id, 'nombre': nuevo.nombre}}), 201

    except Exception as e:
        print(f"Error creando comercio: {e}")
        return jsonify({'success': False, 'message': 'Error interno', 'error': str(e)}), 500


@comercio_crud.route('/api/comercio/login', methods=['POST'])
def api_comercio_login():
    """Login muy simple por email o comercio_id. Guarda `comercio_id` en sesión."""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        comercio_id = data.get('comercio_id')

        with get_db_session() as db_session:
            if comercio_id:
                c = db_session.query(Comercio).filter_by(id=int(comercio_id)).first()
                if not c:
                    return jsonify({'success': False, 'message': 'Comercio no encontrado'}), 404
            elif email:
                usuario = db_session.query(Usuario).filter_by(correo_electronico=email).first()
                if not usuario:
                    return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
                c = db_session.query(Comercio).filter_by(user_id=usuario.id).first()
                if not c:
                    return jsonify({'success': False, 'message': 'No se encontró comercio para ese usuario'}), 404
            else:
                return jsonify({'success': False, 'message': 'Falta email o comercio_id'}), 400

            session['comercio_id'] = c.id
            session['comercio_nombre'] = c.nombre
            return jsonify({'success': True, 'comercio': {'id': c.id, 'nombre': c.nombre}}), 200
    except Exception as e:
        print('Error login comercio:', e)
        return jsonify({'success': False, 'message': 'Error interno', 'error': str(e)}), 500


@comercio_crud.route('/api/comercio/logout', methods=['POST'])
def api_comercio_logout():
    session.pop('comercio_id', None)
    session.pop('comercio_nombre', None)
    return jsonify({'success': True}), 200


@comercio_crud.route('/api/comercios', methods=['GET'])
def api_comercios_list():
    user_id = request.args.get('user_id')
    with get_db_session() as db_session:
        q = db_session.query(Comercio).order_by(Comercio.id.desc())
        if user_id:
            try:
                q = q.filter(Comercio.user_id == int(user_id))
            except Exception:
                pass
        comercios = q.all()
        result = []
        for c in comercios:
            result.append({
                'id': c.id,
                'user_id': c.user_id,
                'nombre': c.nombre,
                'email': c.email,
                'telefono': c.telefono,
                'direccion': c.direccion,
                'ambito': c.ambito,
                'categoria_id': c.categoria_id,
                'activo': c.activo
            })
        return jsonify({'success': True, 'comercios': result}), 200


@comercio_crud.route('/api/comercios/by_email', methods=['GET'])
def api_comercios_by_email():
    email = request.args.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Falta parametro email'}), 400
    with get_db_session() as db_session:
        usuario = db_session.query(Usuario).filter_by(correo_electronico=email).first()
        if not usuario:
            return jsonify({'success': True, 'comercios': []}), 200
        comercios = db_session.query(Comercio).filter_by(user_id=usuario.id).order_by(Comercio.id.desc()).all()
        result = []
        for c in comercios:
            result.append({
                'id': c.id,
                'user_id': c.user_id,
                'nombre': c.nombre,
                'email': c.email,
                'telefono': c.telefono,
                'direccion': c.direccion,
                'ambito': c.ambito,
                'categoria_id': c.categoria_id,
                'activo': c.activo
            })
        return jsonify({'success': True, 'comercios': result}), 200


@comercio_crud.route('/api/comercio/<int:comercio_id>', methods=['GET'])
def api_comercio_get(comercio_id):
    with get_db_session() as db_session:
        c = db_session.query(Comercio).filter_by(id=comercio_id).first()
        if not c:
            return jsonify({'success': False, 'message': 'Comercio no encontrado'}), 404
        return jsonify({'success': True, 'comercio': {
            'id': c.id,
            'nombre': c.nombre,
            'email': c.email,
            'telefono': c.telefono,
            'direccion': c.direccion,
            'latitud': c.latitud,
            'longitud': c.longitud,
            'ambito': c.ambito,
            'categoria_id': c.categoria_id
        }}), 200


@comercio_crud.route('/api/comercio/<int:comercio_id>', methods=['PUT'])
def api_comercio_update(comercio_id):
    data = request.get_json() or {}
    try:
        with get_db_session() as db_session:
            c = db_session.query(Comercio).filter_by(id=comercio_id).first()
            if not c:
                return jsonify({'success': False, 'message': 'Comercio no encontrado'}), 404

            c.nombre = data.get('nombre', c.nombre)
            c.telefono = data.get('telefono', c.telefono)
            c.email = data.get('email', c.email)
            c.direccion = data.get('direccion', c.direccion)
            c.latitud = data.get('latitud', c.latitud)
            c.longitud = data.get('longitud', c.longitud)
            c.ambito = data.get('ambito', c.ambito)
            c.categoria_id = data.get('categoria_id', c.categoria_id)
            c.activo = data.get('activo', c.activo)

            db_session.add(c)
            db_session.flush()

            return jsonify({'success': True, 'message': 'Comercio actualizado', 'comercio': {'id': c.id, 'nombre': c.nombre}}), 200
    except Exception as e:
        print(f"Error actualizando comercio: {e}")
        return jsonify({'success': False, 'message': 'Error interno', 'error': str(e)}), 500


@comercio_crud.route('/api/comercio/<int:comercio_id>', methods=['DELETE'])
def api_comercio_delete(comercio_id):
    try:
        with get_db_session() as db_session:
            c = db_session.query(Comercio).filter_by(id=comercio_id).first()
            if not c:
                return jsonify({'success': False, 'message': 'Comercio no encontrado'}), 404
            c.activo = False
            db_session.add(c)
            db_session.flush()
            return jsonify({'success': True, 'message': 'Comercio desactivado'}), 200
    except Exception as e:
        print(f"Error eliminando comercio: {e}")
        return jsonify({'success': False, 'message': 'Error interno', 'error': str(e)}), 500
