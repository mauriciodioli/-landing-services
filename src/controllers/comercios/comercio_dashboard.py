from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import json
from controllers.comercios.comercio_mock import generar_datos_mock_comercio
from models.pedidos.pedidoEntregaPago import PedidoEntregaPago
from models.pedidos.repartidor import Repartidor
from models.comercios.comercio import Comercio
from models.usuario import Usuario
# Asume que tienes un modelo o guardas la config del comercio en una tabla
# de lo contrario, usamos los datos por defecto enviados por la cuenta.
from models.publicaciones.publicaciones import Publicacion
from utils.db_session import get_db_session

comercio_dashboard = Blueprint('comercio_dashboard', __name__, template_folder='templates')




# Asegúrate de importar la función si la pusiste en otro archivo
# from comercio_mock import generar_datos_mock_comercio

@comercio_dashboard.route('/api/comercio/cargar_mock', methods=['POST'])
def api_cargar_mock():
    try:
        resultado = generar_datos_mock_comercio()
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
# Middleware de simulación de autenticación (igual al de repartidores)
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'comercio_id' not in session:
            # Si no hay sesión, puedes redirigir a un login o manejar el bloqueo
            pass
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@comercio_dashboard.route('/comercio/dashboard')
def dashboard_view():
    # Renderiza la plantilla HTML
    return render_template('comercios/comercio_dashboard.html', logged_in=bool(session.get('comercio_id')))

# ============================================
# ENDPOINTS DE DATOS API
# ============================================
@comercio_dashboard.route('/api/comercio/datos_principales', methods=['GET'])
def datos_principales():
    hoy = datetime.now().date()
    
    try:
        with get_db_session() as db_session:
            # Intentar adjuntar información del comercio si está en sesión
            comercio_info = None
            comercio_id_sess = session.get('comercio_id')
            if comercio_id_sess:
                comercio_obj = db_session.query(Comercio).filter_by(id=comercio_id_sess).first()
                if comercio_obj:
                    usuario_rel = None
                    try:
                        usuario_rel = db_session.query(Usuario).filter_by(id=comercio_obj.user_id).first()
                    except Exception:
                        usuario_rel = None
                    comercio_info = {
                            'id': comercio_obj.id,
                            'user_id': comercio_obj.user_id,
                            'nombre': comercio_obj.nombre,
                            'email_usuario': usuario_rel.correo_electronico if usuario_rel else comercio_obj.email,
                            'ambito': comercio_obj.ambito,
                            'categoria_id': comercio_obj.categoria_id,
                            'direccion': comercio_obj.direccion
                    }

            # Construir query base de pedidos JOIN publicacion para permitir filtros
            base_query = db_session.query(PedidoEntregaPago).join(
                Publicacion, PedidoEntregaPago.publicacion_id == Publicacion.id
            )

            # Leer filtros desde query string (GET) o sesión
            args = request.args or {}
            filtro_comercio_id = args.get('comercio_id') or session.get('comercio_id')
            filtro_user_id = args.get('user_id')
            filtro_ambito = args.get('ambito')
            filtro_categoria = args.get('categoria_id')
            filtro_codigo_postal = args.get('codigoPostal')

            filters = []

            # Si recibimos comercio_id, resolvemos su user_id y filtramos por Publicacion.user_id
            if filtro_comercio_id:
                try:
                    comercio_obj = db_session.query(Comercio).filter_by(id=int(filtro_comercio_id)).first()
                    if comercio_obj and comercio_obj.user_id:
                        filters.append(Publicacion.user_id == comercio_obj.user_id)
                except Exception:
                    pass

            # Si se pasó comercio_id por query y aún no tenemos comercio_info por sesión, adjuntarlo
            if not comercio_info and filtro_comercio_id:
                try:
                    comercio_for_response = db_session.query(Comercio).filter_by(id=int(filtro_comercio_id)).first()
                    if comercio_for_response:
                        usuario_rel = None
                        try:
                            usuario_rel = db_session.query(Usuario).filter_by(id=comercio_for_response.user_id).first()
                        except Exception:
                            usuario_rel = None
                        comercio_info = {
                            'id': comercio_for_response.id,
                            'user_id': comercio_for_response.user_id,
                            'nombre': comercio_for_response.nombre,
                            'email_usuario': usuario_rel.correo_electronico if usuario_rel else comercio_for_response.email,
                            'ambito': comercio_for_response.ambito,
                            'categoria_id': comercio_for_response.categoria_id,
                            'direccion': comercio_for_response.direccion
                        }
                except Exception:
                    pass

            # si se pasa user_id directamente
            if filtro_user_id:
                try:
                    filters.append(Publicacion.user_id == int(filtro_user_id))
                except Exception:
                    pass

            if filtro_ambito:
                filters.append(Publicacion.ambito == filtro_ambito)

            if filtro_categoria:
                try:
                    filters.append(Publicacion.categoria_id == int(filtro_categoria))
                except Exception:
                    pass

            if filtro_codigo_postal:
                filters.append(Publicacion.codigoPostal == filtro_codigo_postal)

            # Aplicar filtros si hay
            if filters:
                base_query = base_query.filter(*filters)

            # Obtener pedidos (posiblemente filtrados)
            todos_los_pedidos = base_query.all()

            def fecha_principal(p):
                return getattr(p, 'fecha_creacion', None) or getattr(p, 'fecha_consulta', None) or getattr(p, 'fecha_entrega', None)

            pedidos_hoy = [p for p in todos_los_pedidos if fecha_principal(p) and fecha_principal(p).date() == hoy]
            entregados_hoy = [p for p in pedidos_hoy if getattr(p, 'estado', None) == 'entregado']

            ventas_hoy = sum([float(p.precio_venta or 0) for p in entregados_hoy])
            cant_pedidos_hoy = len(pedidos_hoy)
            ticket_promedio = ventas_hoy / len(entregados_hoy) if entregados_hoy else 0

            # Pedidos activos (aplicar mismos filtros)
            pedidos_activos = base_query.filter(
                PedidoEntregaPago.estado.in_(['pendiente', 'preparacion', 'listo', 'enviado'])
            ).all()

            # Historial reciente (aplicar filtros)
            historial = base_query.filter(
                PedidoEntregaPago.estado.in_(['entregado', 'cancelado'])
            ).order_by(PedidoEntregaPago.id.desc()).limit(30).all()

            # Estructurar respuestas
            return jsonify({
                'comercio': comercio_info,
                "success": True,
                "applied_filters": {
                    'comercio_id': filtro_comercio_id,
                    'user_id': filtro_user_id,
                    'ambito': filtro_ambito,
                    'categoria_id': filtro_categoria,
                    'codigoPostal': filtro_codigo_postal
                },
                "metrics": {
                    "ventas_hoy": round(ventas_hoy, 2),
                    "pedidos_hoy": cant_pedidos_hoy,
                    "ticket_promedio": round(ticket_promedio, 2)
                },
                "pedidos_activos": [{
                    "id": getattr(p, 'id', 0),
                    "estado": getattr(p, 'estado', 'pendiente'),
                    "lugar_entrega": getattr(p, 'lugar_entrega', 'No especificado'),
                    "nombre_cliente": f"{getattr(p, 'nombreCliente', '') or ''} {getattr(p, 'apellidoCliente', '') or ''}".strip() or "Cliente Anónimo",
                    "telefono_cliente": getattr(p, 'telefonoCliente', 'No disponible'),
                    "precio_venta": float(getattr(p, 'precio_venta', 0) or 0),
                    "fecha": fecha_principal(p).isoformat() if fecha_principal(p) else None
                } for p in pedidos_activos],
                "historial": [{
                    "id": getattr(p, 'id', 0),
                    "estado": getattr(p, 'estado', 'Desconocido'),
                    "lugar_entrega": getattr(p, 'lugar_entrega', 'No especificado'),
                    "precio_venta": float(getattr(p, 'precio_venta', 0) or 0),
                    "fecha": fecha_principal(p).isoformat() if fecha_principal(p) else None
                } for p in historial]
            })
    except Exception as e:
        print(f"❌ ERROR en datos_principales: {str(e)}")
        return jsonify({"success": False, "message": "Error interno del servidor", "error": str(e)}), 500


@comercio_dashboard.route('/api/comercio/actualizar_estado', methods=['POST'])
def api_comercio_actualizar_estado():
    """Actualizar el estado de un pedido.

    JSON esperado: { "pedido_id": 123, "estado": "entregado", "comentario": "..." }
    """
    data = request.get_json(force=True, silent=True) or {}
    pedido_id = data.get('pedido_id') or data.get('id')
    nuevo_estado = data.get('estado')
    comentario = data.get('comentario')

    if not pedido_id or not nuevo_estado:
        return jsonify({"success": False, "message": "Faltan parámetros: pedido_id y estado"}), 400

    try:
        with get_db_session() as db_session:
            pedido = db_session.query(PedidoEntregaPago).filter_by(id=pedido_id).first()
            if not pedido:
                return jsonify({"success": False, "message": "Pedido no encontrado"}), 404

            # Actualizar estado y fechas asociadas
            pedido.estado = nuevo_estado
            if nuevo_estado == 'entregado':
                pedido.fecha_entrega = datetime.now()
            if nuevo_estado == 'enviado':
                pedido.fecha_consulta = datetime.now()

            if comentario is not None:
                pedido.comentarioCliente = comentario

            db_session.add(pedido)
            db_session.flush()

            return jsonify({"success": True, "pedido": {"id": pedido.id, "estado": pedido.estado}}), 200

  
    except Exception as e:
        # 🌟 Esto imprimirá el error real en tu terminal de Python para que sepas qué falló
        print(f"❌ ERROR CRÍTICO EN DASHBOARD COMERCIO: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error interno del servidor",
            "error": str(e)
        }), 500