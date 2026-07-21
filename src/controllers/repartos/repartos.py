# ============================================
# IMPORTS
# ============================================

from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from sqlalchemy import and_, func, or_
from datetime import datetime
import urllib.parse
import logging
from geopy.distance import geodesic

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from werkzeug.security import generate_password_hash, check_password_hash
# Imports de modelos
from models.pedidos.pedidoEntregaPago import PedidoEntregaPago
from models.pedidos.repartidor import Repartidor
from models.comercios.comercio import Comercio
# Crear una entrada en Usuario para manejar autenticación
from models.usuario import Usuario
from utils.db_session import get_db_session


# Crear blueprint
repartos = Blueprint('repartos', __name__)


# ============================================
# RUTAS PARA RENDERIZAR HTML
# ============================================

# controllers/repartos/repartos.py

@repartos.route('/repartidores/dashboard')
def repartidores_dashboard():
    """
    Página principal del dashboard de repartidores
    """
    repartidor_id = session.get('repartidor_id')
    repartidor_data = None
    
    if repartidor_id:
        with get_db_session() as db_session:
            # ✅ Desactivar expiración para mantener los datos accesibles
            db_session.expire_on_commit = False
            
            repartidor = db_session.query(Repartidor).filter_by(id=repartidor_id).first()
            
            if repartidor:
                # ✅ Convertir a diccionario para evitar problemas de sesión
                repartidor_data = {
                    'id': repartidor.id,
                    'nombre': repartidor.nombre,
                    'apellido': repartidor.apellido,
                    'email': repartidor.email,
                    'telefono': repartidor.telefono,
                    'activo': repartidor.activo,
                    'disponible': repartidor.disponible,
                    'puntuacion': repartidor.puntuacion
                }
    
    # ✅ Pasar el diccionario en lugar del objeto ORM
    return render_template('repartidores/dashboard.html', repartidor=repartidor_data)

@repartos.route('/repartidores/login')
def repartidores_login():
    """
    Página de login (si quieres una página separada)
    """
    return render_template('repartidores/login.html')


@repartos.route('/repartidores/historial')
def repartidores_historial():
    """
    Página de historial (si quieres una página separada)
    """
    return render_template('repartidores/historial.html')


@repartos.route('/repartidores/analisis')
def repartidores_analisis():
    """
    Página de análisis (si quieres una página separada)
    """
    return render_template('repartidores/analisis.html')


# ============================================
# RUTAS DE API PARA EL DASHBOARD
# ============================================

@repartos.route('/api/repartidor/login', methods=['POST'])
def api_repartidor_login():
    """
    API para login de repartidor
    """
    try:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
       
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email y contraseña requeridos'
            }), 400
        
        with get_db_session() as db_session:
            # Buscar el repartidor por email
            repartidor = db_session.query(Repartidor).filter_by(email=email).first()

            if not repartidor:
                return jsonify({
                    'success': False,
                    'message': 'Email no registrado'
                }), 404

            # ✅ OBTENER EL HASH DE LA CONTRASEÑA
            stored_hash = None
            usuario = db_session.query(Usuario).filter_by(correo_electronico=email).first()  
            # 1. Intentar obtener de repartidor.password
           
            stored_hash = usuario.password
            # 3. Si aún no hay hash, error
            if not stored_hash:
                print(f"❌ No se encontró contraseña para el email: {email}")
                return jsonify({
                    'success': False,
                    'message': 'No hay contraseña configurada para este usuario. Contacta al administrador.'
                }), 400

            # ✅ CONVERTIR A STRING si es bytes
            if isinstance(stored_hash, bytes):
                try:
                    stored_hash = stored_hash.decode('utf-8')
                except Exception:
                    stored_hash = str(stored_hash)
            
            # ✅ LIMPIAR el hash (remover espacios, saltos de línea)
            stored_hash = stored_hash.strip()
            
            print(f"🔑 Hash a verificar: {stored_hash[:30]}...")
            print(f"🔑 Longitud del hash: {len(stored_hash)}")
            
          
            # Verificar hash: soportar bcrypt ($2b$...) y hashes de werkzeug
            is_correct = False
            try:
                if isinstance(stored_hash, str) and stored_hash.startswith('$2'):
                    # bcrypt style hash (e.g. $2b$...)
                    try:
                        import bcrypt
                        is_correct = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
                    except Exception as be:
                        print(f"⚠️ Error al usar bcrypt: {be}")
                        is_correct = False
                else:
                    # intentamos con werkzeug
                    try:
                        is_correct = check_password_hash(stored_hash, password)
                    except Exception as we:
                        print(f"⚠️ Error en check_password_hash: {we}")
                        is_correct = False
            except Exception as e:
                print(f"⚠️ Error verificando contraseña: {e}")
                is_correct = False

            # Fallback: comparar en texto plano si todo lo demás falla
            if not is_correct and stored_hash == password:
                is_correct = True

            if not is_correct:
                return jsonify({
                    'success': False,
                    'message': 'Contraseña incorrecta'
                }), 401
            
            # ✅ Verificar que la cuenta esté activa
            if not repartidor.activo:
                return jsonify({
                    'success': False,
                    'message': 'Cuenta desactivada. Contacta al administrador.'
                }), 403
            
            # Guardar en sesión
            session['repartidor_id'] = repartidor.id
            session['repartidor_nombre'] = repartidor.nombre
            session['repartidor_email'] = repartidor.email

            # Si el usuario asociado tiene un comercio, también lo guardamos en sesión
            try:
                if usuario:
                    comercio = db_session.query(Comercio).filter_by(user_id=usuario.id).first()
                    if comercio:
                        session['comercio_id'] = comercio.id
                        session['comercio_nombre'] = comercio.nombre
            except Exception as se:
                print(f"⚠️ Error buscando comercio para usuario: {se}")
            
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'repartidor': {
                    'id': repartidor.id,
                    'nombre': repartidor.nombre,
                    'apellido': repartidor.apellido,
                    'email': repartidor.email,
                    'telefono': repartidor.telefono,
                    'rating': repartidor.puntuacion or 5.0,
                    'disponible': repartidor.disponible,
                    'activo': repartidor.activo
                }
            }), 200
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Error en el servidor',
            'error': str(e)
        }), 500
@repartos.route('/api/repartidor/register', methods=['POST'])
def api_repartidor_register():
    """
    API para registro de repartidor
    """
    try:
        data = request.get_json() or {}
        
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        email = data.get('email')
        password = data.get('password')
        telefono = data.get('telefono')
        
        # ✅ Validar campos requeridos
        if not all([nombre, apellido, email, password, telefono]):
            return jsonify({
                'success': False,
                'message': 'Todos los campos son requeridos'
            }), 400
        
        # ✅ Validar formato de email
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({
                'success': False,
                'message': 'Formato de email inválido'
            }), 400
        
        # ✅ Validar longitud de contraseña
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'La contraseña debe tener al menos 6 caracteres'
            }), 400
        
        with get_db_session() as db_session:
            # Verificar si el email ya está registrado en Repartidor
            existe = db_session.query(Repartidor).filter_by(email=email).first()
            if existe:
                return jsonify({
                    'success': False,
                    'message': 'Este email ya está registrado'
                }), 400

          

            _usuario = db_session.query(Usuario).filter_by(email=email).first()    

            # Crear nuevo repartidor ligado al usuario
            nuevo_repartidor = Repartidor(
                nombre=nombre,
                apellido=apellido,
                email=email,
                telefono=telefono,
                user_id=_usuario.id,
                activo=True,
                disponible=True,
                puntuacion=5.0,
                pedidos_activos=0,
                latitud=None,
                longitud=None,
                radio_trabajo_km=10.0,
                total_entregas=0,
                total_cancelaciones=0,
                fecha_alta=datetime.now()
            )

            db_session.add(nuevo_repartidor)
            db_session.flush()
            
            # Guardar en sesión
            session['repartidor_id'] = nuevo_repartidor.id
            session['repartidor_nombre'] = nuevo_repartidor.nombre
            session['repartidor_email'] = nuevo_repartidor.email
            
            return jsonify({
                'success': True,
                'message': 'Registro exitoso',
                'repartidor': {
                    'id': nuevo_repartidor.id,
                    'nombre': nuevo_repartidor.nombre,
                    'apellido': nuevo_repartidor.apellido,
                    'email': nuevo_repartidor.email,
                    'telefono': nuevo_repartidor.telefono,
                    'activo': nuevo_repartidor.activo,
                    'disponible': nuevo_repartidor.disponible
                }
            }), 201
            
    except Exception as e:
        logger.error(f"Error en registro: {e}")
        return jsonify({
            'success': False,
            'message': 'Error en el servidor',
            'error': str(e)
        }), 500


@repartos.route('/api/repartidor/logout', methods=['POST'])
def api_repartidor_logout():
    """
    API para cerrar sesión
    """
    try:
        # ✅ Limpiar sesión
        session.pop('repartidor_id', None)
        session.pop('repartidor_nombre', None)
        session.pop('repartidor_email', None)
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'Sesión cerrada correctamente'
        }), 200
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al cerrar sesión',
            'error': str(e)
        }), 500

@repartos.route('/api/repartidor/verificar_sesion', methods=['GET'])
def api_repartidor_verificar_sesion():
    """
    Verificar si hay una sesión activa
    """
    try:
        repartidor_id = session.get('repartidor_id')
        
        if not repartidor_id:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        with get_db_session() as db_session:
            repartidor = db_session.query(Repartidor).filter_by(id=repartidor_id).first()
            
            if not repartidor:
                session.clear()
                return jsonify({
                    'success': False,
                    'message': 'Repartidor no encontrado'
                }), 404
            
            if not repartidor.activo:
                session.clear()
                return jsonify({
                    'success': False,
                    'message': 'Cuenta desactivada'
                }), 403
            
            return jsonify({
                'success': True,
                'repartidor': {
                    'id': repartidor.id,
                    'nombre': repartidor.nombre,
                    'apellido': repartidor.apellido,
                    'email': repartidor.email,
                    'telefono': repartidor.telefono,
                    'rating': repartidor.puntuacion or 5.0,
                    'disponible': repartidor.disponible,
                    'activo': repartidor.activo
                }
            }), 200
            
    except Exception as e:
        print(f"❌ Error verificando sesión: {e}")
        return jsonify({
            'success': False,
            'message': 'Error en el servidor',
            'error': str(e)
        }), 500

# controllers/repartos/repartos.py

@repartos.route('/api/repartidor/configuracion', methods=['GET'])
def api_repartidor_configuracion():
    """
    Obtener configuración del repartidor
    """
    repartidor_id = session.get('repartidor_id')
    
    if not repartidor_id:
        return jsonify({
            'success': False,
            'message': 'No autenticado'
        }), 401
    
    with get_db_session() as db_session:
        repartidor = db_session.query(Repartidor).filter_by(id=repartidor_id).first()
        
        if not repartidor:
            return jsonify({
                'success': False,
                'message': 'Repartidor no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'configuracion': {
                'id': repartidor.id,
                'nombre': repartidor.nombre,
                'apellido': repartidor.apellido,
                'email': repartidor.email,
                'telefono': repartidor.telefono,
                'vehiculo': repartidor.vehiculo,
                'patente': repartidor.patente,
                'radio_trabajo_km': repartidor.radio_trabajo_km,
                'puntuacion': repartidor.puntuacion,
                'disponible': repartidor.disponible,
                'activo': repartidor.activo
            }
        }), 200


@repartos.route('/api/repartidor/configuracion', methods=['PUT'])
def api_repartidor_actualizar_configuracion():
    """
    Actualizar configuración del repartidor
    """
    repartidor_id = session.get('repartidor_id')
    
    if not repartidor_id:
        return jsonify({
            'success': False,
            'message': 'No autenticado'
        }), 401
    
    try:
        data = request.get_json() or {}
        
        with get_db_session() as db_session:
            repartidor = db_session.query(Repartidor).filter_by(id=repartidor_id).first()
            
            if not repartidor:
                return jsonify({
                    'success': False,
                    'message': 'Repartidor no encontrado'
                }), 404
            
            # Actualizar campos
            repartidor.nombre = data.get('nombre', repartidor.nombre)
            repartidor.apellido = data.get('apellido', repartidor.apellido)
            repartidor.email = data.get('email', repartidor.email)
            repartidor.telefono = data.get('telefono', repartidor.telefono)
            repartidor.vehiculo = data.get('vehiculo', repartidor.vehiculo)
            repartidor.patente = data.get('patente', repartidor.patente)
            repartidor.radio_trabajo_km = data.get('radio_trabajo_km', repartidor.radio_trabajo_km)
            repartidor.disponible = data.get('disponible', repartidor.disponible)
            repartidor.activo = data.get('activo', repartidor.activo)
            repartidor.ultima_actualizacion = datetime.now()
            
            db_session.commit()
            
            # Devolver datos actualizados
            return jsonify({
                'success': True,
                'message': 'Configuración actualizada',
                'repartidor': {
                    'id': repartidor.id,
                    'nombre': repartidor.nombre,
                    'apellido': repartidor.apellido,
                    'email': repartidor.email,
                    'telefono': repartidor.telefono,
                    'vehiculo': repartidor.vehiculo,
                    'patente': repartidor.patente,
                    'radio_trabajo_km': repartidor.radio_trabajo_km,
                    'puntuacion': repartidor.puntuacion,
                    'disponible': repartidor.disponible,
                    'activo': repartidor.activo
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Error actualizando configuración: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al actualizar',
            'error': str(e)
        }), 500
        
        
        
        

@repartos.route('/api/repartidor/pedidos', methods=['GET'])
def api_repartidor_pedidos():
    """
    API para obtener pedidos del repartidor
    """
    try:
        repartidor_id = session.get('repartidor_id')
        
        if not repartidor_id:
            return jsonify({
                'success': False,
                'message': 'No autenticado'
            }), 401
        
        with get_db_session() as db_session:
            # Filtrar pedidos cuyo campo 'asignado_a' coincide con el id del repartidor
            pedidos = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.asignado_a == str(repartidor_id)
            ).order_by(PedidoEntregaPago.fecha_creacion.desc()).all()
            
            pedidos_data = []
            for p in pedidos:
                pedidos_data.append({
                    'id': p.id,
                    'cliente': f"{p.nombreCliente or ''} {p.apellidoCliente or ''}",
                    'fecha': p.fecha_creacion.strftime('%Y-%m-%d') if p.fecha_creacion else '',
                    'total': float(p.precio_venta or 0),
                    'comision': float(p.precio_venta or 0) * 0.1,  # 10% comisión
                    'estado': p.estado,
                    'lugar_entrega': p.lugar_entrega
                })
            
            return jsonify({
                'success': True,
                'pedidos': pedidos_data,
                'total': len(pedidos_data)
            }), 200
            
    except Exception as e:
        logger.error(f"Error obteniendo pedidos: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener pedidos',
            'error': str(e)
        }), 500


@repartos.route('/api/repartidor/estadisticas', methods=['GET'])
def api_repartidor_estadisticas():
    """
    API para obtener estadísticas del repartidor
    """
    try:
        repartidor_id = session.get('repartidor_id')
        
        if not repartidor_id:
            return jsonify({
                'success': False,
                'message': 'No autenticado'
            }), 401
        
        with get_db_session() as db_session:
            # Obtener repartidor
            repartidor = db_session.query(Repartidor).filter_by(id=repartidor_id).first()
            
            # Pedidos completados
            completados = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.repartidor_id == repartidor_id,
                PedidoEntregaPago.estado == 'entregado'
            ).all()
            
            # Pedidos en curso
            en_curso = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.repartidor_id == repartidor_id,
                PedidoEntregaPago.estado.in_(['pendiente', 'enviado'])
            ).count()
            
            # Total ganado (10% comisión)
            total_ganado = sum(float(p.precio_venta or 0) * 0.1 for p in completados)
            
            # Pedidos hoy
            hoy = datetime.now().date()
            pedidos_hoy = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.repartidor_id == repartidor_id,
                func.date(PedidoEntregaPago.fecha_creacion) == hoy
            ).count()
            
            return jsonify({
                'success': True,
                'estadisticas': {
                    'total_pedidos': len(completados) + en_curso,
                    'pedidos_hoy': pedidos_hoy,
                    'comisiones': total_ganado,
                    'rating': repartidor.puntuacion or 5.0,
                    'pedidos_activos': en_curso,
                    'total_ganado': total_ganado,
                    'promedio_pedido': total_ganado / len(completados) if completados else 0,
                    'tasa_exito': round((len(completados) / (len(completados) + en_curso)) * 100 if (len(completados) + en_curso) > 0 else 0, 1)
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener estadísticas',
            'error': str(e)
        }), 500


@repartos.route('/api/repartidor/pedidos/<int:pedido_id>/comentario', methods=['POST'])
def api_repartidor_pedido_comentario(pedido_id):
    """
    API para agregar/actualizar un comentario del repartidor sobre un pedido
    """
    try:
        repartidor_id = session.get('repartidor_id')
        if not repartidor_id:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401

        data = request.get_json() or {}
        comentario = data.get('comentario')
        if comentario is None:
            return jsonify({'success': False, 'message': 'Falta comentario'}), 400

        with get_db_session() as db_session:
            pedido = db_session.query(PedidoEntregaPago).filter_by(id=pedido_id, repartidor_id=repartidor_id).first()
            if not pedido:
                return jsonify({'success': False, 'message': 'Pedido no encontrado'}), 404

            pedido.comentarioCliente = comentario
            db_session.add(pedido)
            db_session.commit()

            return jsonify({'success': True, 'message': 'Comentario guardado', 'pedido_id': pedido.id}), 200

    except Exception as e:
        logger.error(f"Error guardando comentario: {e}")
        return jsonify({'success': False, 'message': 'Error al guardar comentario', 'error': str(e)}), 500


@repartos.route('/api/repartidor/pedidos/<int:pedido_id>/aceptar', methods=['POST'])
def api_repartidor_pedido_aceptar(pedido_id):
    """Permite al repartidor asignado aceptar el pedido (pendiente -> enviado)."""
    try:
        repartidor_id = session.get('repartidor_id')
        if not repartidor_id:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401

        with get_db_session() as db_session:
            pedido = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.id == pedido_id,
                PedidoEntregaPago.asignado_a == str(repartidor_id)
            ).first()

            if not pedido:
                return jsonify({'success': False, 'message': 'Pedido no encontrado o no te corresponde'}), 404

            estado_actual = (pedido.estado or '').lower()
            if estado_actual not in ['', 'pendiente', 'por_asignar']:
                return jsonify({'success': False, 'message': 'El pedido no está en estado pendiente'}), 400

            pedido.estado = 'enviado'
            pedido.fecha_consulta = datetime.now()  # reutilizamos fecha_consulta como fecha de aceptación
            db_session.add(pedido)
            db_session.commit()

            return jsonify({'success': True, 'message': 'Pedido aceptado', 'pedido_id': pedido.id}), 200

    except Exception as e:
        logger.error(f"Error aceptando pedido: {e}")
        return jsonify({'success': False, 'message': 'Error al aceptar pedido', 'error': str(e)}), 500


@repartos.route('/api/repartidor/pedidos/<int:pedido_id>/marcar', methods=['POST'])
def api_repartidor_pedido_marcar(pedido_id):
    """Marcar pedido como entregado o como no_corresponde.
    Body: { action: 'entregado'|'no_corresponde', comentario: optional }
    """
    try:
        repartidor_id = session.get('repartidor_id')
        if not repartidor_id:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401

        data = request.get_json() or {}
        action = (data.get('action') or '').lower()
        comentario = data.get('comentario')

        if action not in ['entregado', 'no_corresponde']:
            return jsonify({'success': False, 'message': 'Acción inválida'}), 400

        with get_db_session() as db_session:
            pedido = db_session.query(PedidoEntregaPago).filter(
                PedidoEntregaPago.id == pedido_id,
                PedidoEntregaPago.asignado_a == str(repartidor_id)
            ).first()

            if not pedido:
                return jsonify({'success': False, 'message': 'Pedido no encontrado o no te corresponde'}), 404

            estado_actual = (pedido.estado or '').lower()
            if action == 'entregado':
                if estado_actual not in ['enviado', 'en_curso', 'en_transito']:
                    return jsonify({'success': False, 'message': 'El pedido no está en curso'}), 400
                pedido.estado = 'entregado'
                pedido.fecha_entrega = datetime.now()
                if comentario:
                    pedido.comentarioCliente = comentario

            else:  # no_corresponde
                # aceptar comentario obligatorio
                if not comentario:
                    return jsonify({'success': False, 'message': 'Comentario requerido para no_corresponde'}), 400
                pedido.estado = 'no_corresponde'
                pedido.comentarioCliente = comentario

            db_session.add(pedido)
            db_session.commit()

            return jsonify({'success': True, 'message': 'Estado actualizado', 'pedido_id': pedido.id}), 200

    except Exception as e:
        logger.error(f"Error marcando pedido: {e}")
        return jsonify({'success': False, 'message': 'Error al actualizar estado', 'error': str(e)}), 500




# ============================================
# FUNCIONES AUXILIARES (las que ya tenías)
# ============================================

def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula distancia en kilómetros usando geodesic"""
    return geodesic(
        (float(lat1), float(lon1)),
        (float(lat2), float(lon2))
    ).km


def calcular_costo_repartidor(repartidor_lat, repartidor_lon, 
                              comercio_lat, comercio_lon, 
                              cliente_lat, cliente_lon):
    """Calcula distancias para un repartidor"""
    distancia_repartidor_comercio = calcular_distancia_km(
        repartidor_lat, repartidor_lon,
        comercio_lat, comercio_lon
    )
    
    distancia_comercio_cliente = calcular_distancia_km(
        comercio_lat, comercio_lon,
        cliente_lat, cliente_lon
    )
    
    distancia_total = distancia_repartidor_comercio + distancia_comercio_cliente
    
    return {
        "distancia_repartidor_comercio": round(distancia_repartidor_comercio, 2),
        "distancia_comercio_cliente": round(distancia_comercio_cliente, 2),
        "distancia_total": round(distancia_total, 2)
    }


def calcular_score_repartidor(repartidor, distancias, pedidos_activos_max=5):
    """Calcula el score para seleccionar el mejor repartidor"""
    # ✅ Asegurar que pedidos_activos no sea None
    pedidos_activos = repartidor.pedidos_activos or 0
    
    # Factores de ponderación
    PESO_DISTANCIA = 0.6
    PESO_PEDIDOS = 0.3
    PESO_PUNTUACION = 0.1
    
    # Normalizar pedidos activos (0-1)
    pedidos_normalizado = pedidos_activos / pedidos_activos_max if pedidos_activos_max > 0 else 0
    
    # Normalizar puntuación (0-1) asumiendo que es de 1-5
    puntuacion_normalizada = (repartidor.puntuacion or 3) / 5
    
    # Score combinado (menor es mejor)
    score = (
        PESO_DISTANCIA * distancias["distancia_total"] +
        PESO_PEDIDOS * pedidos_normalizado * 10 +
        (1 - PESO_PUNTUACION * puntuacion_normalizada)
    )
    
    return round(score, 2)


def generar_mensaje_whatsapp(pedido, repartidor, direccion_local, direccion_cliente, ruta_maps):
    """Genera el mensaje para WhatsApp"""
    mensaje = f"""
🚴 NUEVO REPARTO

Pedido #{pedido.id}

🏪 RETIRAR EN:
{direccion_local}

📦 ENTREGAR EN:
{direccion_cliente}

👤 CLIENTE:
{pedido.nombreCliente or ''} {pedido.apellidoCliente or ''}

📞 CLIENTE:
{pedido.telefonoCliente or 'No disponible'}

💰 IMPORTE:
${pedido.precio_venta or 'No informado'}

🚴 REPARTIDOR:
{repartidor['nombre']}

📏 Distancia repartidor → local:
{repartidor['distancia_repartidor_comercio']} km

📏 Distancia local → cliente:
{repartidor['distancia_comercio_cliente']} km

📏 Distancia total:
{repartidor['distancia_total']} km

🗺 RUTA:
{ruta_maps}
"""
    return mensaje


# ============================================
# ENDPOINTS DE ENVÍO DE PEDIDOS (los que ya tenías)
# ============================================

@repartos.route('/productosComerciales_pedidos_repartos_enviar_pedido/', methods=['POST'])
def productosComerciales_pedidos_repartos_enviar_pedido():
    """
    Endpoint para enviar un pedido a un repartidor
    """
    try:
        data = request.get_json() or {}
        pedido_id = data.get('pedido_id')
        
        if not pedido_id:
            return jsonify({
                'success': False,
                'message': 'Falta pedido_id'
            }), 400
        
        cliente_lat = float(data.get('cliente_lat', 0))
        cliente_lon = float(data.get('cliente_lon', 0))
        
        if cliente_lat == 0 or cliente_lon == 0:
            return jsonify({
                'success': False,
                'message': 'Coordenadas del cliente no proporcionadas'
            }), 400
        
        with get_db_session() as db_session:
            pedido = db_session.query(PedidoEntregaPago).filter_by(id=pedido_id).first()
            
            if not pedido:
                return jsonify({
                    'success': False,
                    'message': 'Pedido no encontrado'
                }), 404
            
            if pedido.estado == "enviado":
                return jsonify({
                    'success': False,
                    'message': 'El pedido ya fue enviado'
                }), 400
            
            comercio_lat = float(data.get('comercio_lat', 42.7345))
            comercio_lon = float(data.get('comercio_lon', 12.7388))
            direccion_local = data.get('direccion_local', 'Via Roma 12, Spoleto')
            direccion_cliente = pedido.lugar_entrega or "Dirección no especificada"
            
            repartidores = db_session.query(Repartidor).filter(
                Repartidor.activo == True,
                Repartidor.disponible == True,
                Repartidor.latitud.isnot(None),
                Repartidor.longitud.isnot(None)
            ).all()
            
            if not repartidores:
                return jsonify({
                    'success': False,
                    'message': 'No hay repartidores disponibles'
                }), 404
            
            mejor_repartidor = None
            mejor_score = float("inf")
            repartidores_evaluados = []
            
            for repartidor in repartidores:
                distancias = calcular_costo_repartidor(
                    repartidor.latitud, repartidor.longitud,
                    comercio_lat, comercio_lon,
                    cliente_lat, cliente_lon
                )
                
                score = calcular_score_repartidor(repartidor, distancias)
                
                repartidor_info = {
                    "id": repartidor.id,
                    "nombre": repartidor.nombre,
                    "apellido": repartidor.apellido,
                    "telefono": repartidor.telefono,
                    "distancia_repartidor_comercio": distancias["distancia_repartidor_comercio"],
                    "distancia_comercio_cliente": distancias["distancia_comercio_cliente"],
                    "distancia_total": distancias["distancia_total"],
                    "score": score,
                    "pedidos_activos": repartidor.pedidos_activos or 0,
                    "puntuacion": repartidor.puntuacion or 5
                }
                
                repartidores_evaluados.append(repartidor_info)
                
                if score < mejor_score:
                    mejor_score = score
                    mejor_repartidor = repartidor_info
            
            # Actualizar pedido
            pedido.estado = "enviado"
            pedido.fecha_envio = datetime.now()
            pedido.repartidor_id = mejor_repartidor["id"]
            
            # Actualizar pedidos activos del repartidor
            repartidor_asignado = db_session.query(Repartidor).filter_by(id=mejor_repartidor["id"]).first()
            if repartidor_asignado:
                repartidor_asignado.pedidos_activos = (repartidor_asignado.pedidos_activos or 0) + 1
            
            # Generar ruta y mensaje
            ruta_maps = (
                f"https://www.google.com/maps/dir/"
                f"{urllib.parse.quote(direccion_local)}/"
                f"{urllib.parse.quote(direccion_cliente)}"
            )
            
            mensaje = generar_mensaje_whatsapp(
                pedido, mejor_repartidor, 
                direccion_local, direccion_cliente, 
                ruta_maps
            )
            
            whatsapp_url = (
                f"https://wa.me/{mejor_repartidor['telefono']}"
                f"?text={urllib.parse.quote(mensaje)}"
            )
            
            db_session.commit()
            
            return jsonify({
                "success": True,
                "message": "Pedido enviado correctamente",
                "pedido_id": pedido.id,
                "estado": pedido.estado,
                "fecha_envio": pedido.fecha_envio.isoformat() if pedido.fecha_envio else None,
                "repartidor": mejor_repartidor,
                "repartidores_evaluados": repartidores_evaluados,
                "ruta_maps": ruta_maps,
                "whatsapp_url": whatsapp_url,
                "mensaje_whatsapp": mensaje
            }), 200
            
    except ValueError as ve:
        logger.error(f"Error de valor: {ve}")
        return jsonify({
            'success': False,
            'message': 'Error en los datos proporcionados',
            'error': str(ve)
        }), 400
    
    except Exception as e:
        logger.error(f"Error al enviar pedido: {e}")
        return jsonify({
            'success': False,
            'message': 'Error al enviar el pedido',
            'error': str(e)
        }), 500