from flask import Blueprint, jsonify, request

from extensions import db
from services.sip_service import SipService


campania_telefonica_bp = Blueprint('campania_telefonica_bp', __name__)


@campania_telefonica_bp.route('/campaniaTelefonica/generarSipLink/', methods=['POST'])
def generar_sip_link():
    data = request.get_json(silent=True) or {}
    telefono = data.get('telefono')
    usuario_id = data.get('usuario_id')
    campania_id = data.get('campania_id')

    try:
        sip_link = SipService.generar_sip_link(telefono)
        SipService.registrar_log_llamada(
            telefono=SipService.normalizar_telefono(telefono),
            usuario_id=usuario_id,
            campania_id=campania_id,
        )
        return jsonify({'success': True, 'sip_link': sip_link}), 200
    except ValueError as e:
        SipService.registrar_log_error(
            telefono=telefono,
            error=e,
            usuario_id=usuario_id,
            campania_id=campania_id,
        )
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        SipService.registrar_log_error(
            telefono=telefono,
            error=e,
            usuario_id=usuario_id,
            campania_id=campania_id,
        )
        return jsonify({'success': False, 'error': 'No fue posible generar el enlace SIP'}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass