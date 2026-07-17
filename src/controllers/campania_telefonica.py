import hmac
import importlib

from flask import Blueprint, current_app, jsonify, render_template, request, session
from sqlalchemy import or_, text
from werkzeug.security import check_password_hash

from extensions import db
from models.campania_contacto import CampaniaContacto
from models.campania_telefonica import CampaniaEstado, CampaniaTelefonica
from models.contacto_telefonico import ContactoTelefonico
from models.historial_contacto import HistorialContacto
from services.importador_sheet_service import ImportadorSheetService
from services import SipService


campania_telefonica = Blueprint("campania_telefonica", __name__)
importador_service = ImportadorSheetService()


try:
    bcrypt = importlib.import_module("bcrypt")
except ImportError:
    bcrypt = None


IMPORTADOR_SESSION_KEY = "campania_importador_auth"


def serializar_campania(campania: CampaniaTelefonica) -> dict:
    return {
        "id": campania.id,
        "usuario_creador_id": campania.usuario_creador_id,
        "nombre": campania.nombre,
        "sheet_id": campania.sheet_id,
        "sheet_name": campania.sheet_name,
        "sheet_tab": campania.sheet_tab,
        "estado": campania.estado,
        "total_registros": campania.total_registros,
        "fecha_creacion": campania.fecha_creacion.isoformat() if campania.fecha_creacion else None,
    }


def serializar_campania_contacto(relation: CampaniaContacto) -> dict:
    contacto = relation.contacto
    dial_number = importador_service.normalizar_telefono_discado(
        contacto.telefono_original or contacto.telefono_normalizado
    )
    return {
        "id": relation.id,
        "campania_id": relation.campania_id,
        "contacto_id": relation.contacto_id,
        "usuario_asignado_id": relation.usuario_asignado_id,
        "estado": relation.estado,
        "cantidad_intentos": relation.cantidad_intentos,
        "fecha_ultimo_contacto": relation.fecha_ultimo_contacto.isoformat() if relation.fecha_ultimo_contacto else None,
        "observacion": relation.observacion,
        "eliminado": relation.eliminado,
        "exitoso": relation.exitoso,
        "fecha_creacion": relation.fecha_creacion.isoformat() if relation.fecha_creacion else None,
        "contacto": {
            "id": contacto.id,
            "telefono_normalizado": contacto.telefono_normalizado,
            "telefono_original": contacto.telefono_original,
            "telefono_discado": dial_number,
            "empresa": contacto.empresa,
            "ciudad": contacto.ciudad,
            "email": contacto.email,
            "web": contacto.web,
            "estado_global": contacto.estado_global,
            "fecha_creacion": contacto.fecha_creacion.isoformat() if contacto.fecha_creacion else None,
        },
        "acciones": {
            "sip_uri": importador_service.construir_sip_uri(contacto.telefono_original or contacto.telefono_normalizado),
            "whatsapp_uri": importador_service.construir_whatsapp_uri(contacto.telefono_original or contacto.telefono_normalizado),
            "sms_uri": importador_service.construir_sms_uri(contacto.telefono_original or contacto.telefono_normalizado),
        },
    }


def serializar_historial(item: HistorialContacto) -> dict:
    return {
        "id": item.id,
        "campania_contacto_id": item.campania_contacto_id,
        "usuario_id": item.usuario_id,
        "accion": item.accion,
        "estado_anterior": item.estado_anterior,
        "estado_nuevo": item.estado_nuevo,
        "nota": item.nota,
        "fecha": item.fecha.isoformat() if item.fecha else None,
    }


def construir_contexto_sip() -> dict:
    try:
        sip_config = SipService.get_sip_config()
        return {
            "sip_provider": SipService.get_provider_label(),
            "sip_server": sip_config.get("server") or "No configurado",
            "sip_user": sip_config.get("user") or "No configurado",
            "sip_caller_id": sip_config.get("caller_id") or "No configurado",
            "sip_softphone": "Zoiper",
            "sip_ready": True,
            "sip_error": None,
        }
    except Exception as exc:
        return {
            "sip_provider": SipService.get_provider_label(),
            "sip_server": "No configurado",
            "sip_user": "No configurado",
            "sip_caller_id": "No configurado",
            "sip_softphone": "Zoiper",
            "sip_ready": False,
            "sip_error": str(exc),
        }


def _normalizar_password_guardado(stored_password):
    if stored_password is None:
        return b"", ""

    if isinstance(stored_password, memoryview):
        stored_password = stored_password.tobytes()

    if isinstance(stored_password, bytes):
        return stored_password, stored_password.decode("utf-8", errors="ignore")

    stored_text = str(stored_password)
    return stored_text.encode("utf-8"), stored_text


def _verificar_password_usuario(stored_password, plain_password: str) -> bool:
    if not plain_password:
        return False

    stored_bytes, stored_text = _normalizar_password_guardado(stored_password)
    candidate_bytes = plain_password.encode("utf-8")

    if bcrypt and (stored_bytes.startswith(b"$2a$") or stored_bytes.startswith(b"$2b$") or stored_bytes.startswith(b"$2y$")):
        try:
            return bcrypt.checkpw(candidate_bytes, stored_bytes)
        except ValueError:
            return False

    if stored_text.startswith("pbkdf2:") or stored_text.startswith("scrypt:"):
        try:
            return check_password_hash(stored_text, plain_password)
        except ValueError:
            return False

    return hmac.compare_digest(stored_text, plain_password)


def _consultar_usuario_por_correo(correo_electronico: str):
    return (
        db.session.execute(
            text(
                """
                SELECT id, correo_electronico, password, activo, roll
                FROM usuarios
                WHERE LOWER(correo_electronico) = :correo_electronico
                LIMIT 1
                """
            ),
            {"correo_electronico": correo_electronico},
        )
        .mappings()
        .first()
    )


def _consultar_usuario_por_access_token(access_token: str):
    return (
        db.session.execute(
            text(
                """
                SELECT id, correo_electronico, password, activo, roll, token
                FROM usuarios
                WHERE token = :access_token
                LIMIT 1
                """
            ),
            {"access_token": access_token},
        )
        .mappings()
        .first()
    )


def _extraer_access_token(payload: dict) -> str:
    access_token = (payload.get("access_token") or "").strip()
    if access_token:
        return access_token

    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return ""


def _construir_usuario_auth(usuario) -> dict:
    return {
        "id": int(usuario["id"]),
        "correo_electronico": usuario["correo_electronico"],
        "roll": usuario.get("roll"),
    }


def autenticar_usuario_importador_por_token(payload: dict, *, persistir_sesion: bool = True):
    access_token = _extraer_access_token(payload)
    if not access_token:
        return None, (401, "No hay access_token disponible")

    usuario = _consultar_usuario_por_access_token(access_token)
    if not usuario:
        return None, (401, "Access token invalido")
    if not bool(usuario.get("activo")):
        return None, (403, "Usuario inactivo")

    usuario_auth = _construir_usuario_auth(usuario)
    if persistir_sesion:
        session[IMPORTADOR_SESSION_KEY] = usuario_auth

    return usuario_auth, None


def autenticar_usuario_importador(payload: dict, *, persistir_sesion: bool = True):
    access_token = _extraer_access_token(payload)
    if access_token and not (payload.get("correo_electronico") or payload.get("email") or payload.get("password")):
        return autenticar_usuario_importador_por_token(payload, persistir_sesion=persistir_sesion)

    correo_electronico = (payload.get("correo_electronico") or payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not correo_electronico:
        return None, (400, "Debes ingresar el correo electronico")
    if not password:
        return None, (400, "Debes ingresar el password")

    usuario = _consultar_usuario_por_correo(correo_electronico)
    if not usuario:
        return None, (404, "Usuario no encontrado")
    if not bool(usuario.get("activo")):
        return None, (403, "Usuario inactivo")
    if not _verificar_password_usuario(usuario.get("password"), password):
        return None, (401, "Credenciales invalidas")

    if not bcrypt and _normalizar_password_guardado(usuario.get("password"))[0].startswith((b"$2a$", b"$2b$", b"$2y$")):
        return None, (500, "Falta la libreria bcrypt para validar este usuario")

    usuario_auth = _construir_usuario_auth(usuario)

    if persistir_sesion:
        session[IMPORTADOR_SESSION_KEY] = usuario_auth

    return usuario_auth, None


def resolver_usuario_importador(payload: dict):
    access_token = _extraer_access_token(payload)
    if access_token:
        return autenticar_usuario_importador_por_token(payload, persistir_sesion=True)

    if payload.get("password"):
        return autenticar_usuario_importador(payload, persistir_sesion=True)

    usuario_auth = session.get(IMPORTADOR_SESSION_KEY)
    if not usuario_auth or not usuario_auth.get("id"):
        return None, (401, "Debes iniciar sesion antes de analizar o importar la hoja")

    return usuario_auth, None


def resolver_usuario_importador_requerido():
    usuario_auth, error = resolver_usuario_importador({})
    if error:
        code, message = error
        return None, jsonify({"ok": False, "error": message}), code

    return usuario_auth, None, None


def obtener_campania_del_usuario(campania_id: int, usuario_id: int):
    return (
        db.session.query(CampaniaTelefonica)
        .filter(
            CampaniaTelefonica.id == campania_id,
            CampaniaTelefonica.usuario_creador_id == usuario_id,
        )
        .first()
    )


@campania_telefonica.get("/admin/campania-telefonica/ui/")
def campania_telefonica_ui():
    return render_template(
        "campaniaTelefonica/index.html",
        estados=[item.value for item in CampaniaEstado],
        **construir_contexto_sip(),
    )


@campania_telefonica.get("/admin/campania-telefonica/tutorial/")
def campania_telefonica_tutorial():
    return render_template(
        "campaniaTelefonica/tutorial_operadores.html",
        **construir_contexto_sip(),
    )


@campania_telefonica.get("/admin/campania-telefonica/guia-sip/")
def campania_telefonica_guia_sip():
    return jsonify({"ok": False, "error": "Ruta deshabilitada"}), 404


@campania_telefonica.post("/admin/campania-telefonica/auth-importador/")
def autenticar_importador_sheet():
    payload = request.get_json(silent=True) or {}

    try:
        usuario_auth, error = autenticar_usuario_importador(payload, persistir_sesion=True)
        if error:
            code, message = error
            return jsonify({"ok": False, "error": message}), code

        return jsonify({"ok": True, "user": usuario_auth}), 200
    except Exception as exc:
        current_app.logger.exception("Error autenticando importador de campania")
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.get("/admin/campania-telefonica/auth-importador/")
def sesion_importador_sheet():
    payload = {"access_token": _extraer_access_token({})}

    try:
        usuario_auth, error = resolver_usuario_importador(payload)
        if error:
            code, message = error
            return jsonify({"ok": False, "error": message}), code

        return jsonify({"ok": True, "user": usuario_auth}), 200
    except Exception as exc:
        current_app.logger.exception("Error consultando sesion del importador")
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.post("/admin/campania-telefonica/analizar/")
def analizar_campania_sheet():
    payload = request.get_json(silent=True) or {}

    try:
        usuario_auth, error = resolver_usuario_importador(payload)
        if error:
            code, message = error
            return jsonify({"ok": False, "error": message}), code

        analysis = importador_service.analizar_sheet(
            sheet_id=payload.get("sheet_id"),
            sheet_tab=payload.get("sheet_tab"),
            cantidad_registros=payload.get("cantidad_registros"),
        )
        return jsonify({"ok": True, "user": usuario_auth, **analysis}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.post("/admin/campania-telefonica/importar/")
def importar_campania_sheet():
    payload = request.get_json(silent=True) or {}

    try:
        usuario_auth, error = resolver_usuario_importador(payload)
        if error:
            code, message = error
            return jsonify({"ok": False, "error": message}), code

        result = importador_service.importar_desde_sheet(
            sheet_id=payload.get("sheet_id"),
            sheet_name=payload.get("sheet_name") or payload.get("sheet_id"),
            sheet_tab=payload.get("sheet_tab"),
            nombre_campania=payload.get("nombre") or payload.get("sheet_tab") or "Campania telefonica",
            usuario_creador_id=usuario_auth["id"],
            cantidad_registros=payload.get("cantidad_registros"),
        )
        return jsonify({"ok": True, "user": usuario_auth, **result}), 201
    except Exception as e:
        current_app.logger.exception("Error importando campania telefonica")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.get("/admin/campania-telefonica/")
def listar_campanias():
    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        page = max(1, request.args.get("page", default=1, type=int))
        page_size = min(max(1, request.args.get("page_size", default=20, type=int)), 100)
        estado = request.args.get("estado")
        usuario_creador_id = usuario_auth["id"]

        query = db.session.query(CampaniaTelefonica)
        if estado:
            query = query.filter(CampaniaTelefonica.estado == estado)
        query = query.filter(CampaniaTelefonica.usuario_creador_id == usuario_creador_id)

        total = query.count()
        items = (
            query.order_by(CampaniaTelefonica.fecha_creacion.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            .all()
        )

        return jsonify({
            "ok": True,
            "user": usuario_auth,
            "items": [serializar_campania(item) for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": (page * page_size) < total,
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.get("/admin/campania-telefonica/historial/")
def historial_campanias_usuario():
    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        limit = min(max(1, request.args.get("limit", default=20, type=int)), 50)
        items = (
            db.session.query(CampaniaTelefonica)
            .filter(CampaniaTelefonica.usuario_creador_id == usuario_auth["id"])
            .order_by(CampaniaTelefonica.fecha_creacion.desc())
            .limit(limit)
            .all()
        )

        return jsonify({
            "ok": True,
            "user": usuario_auth,
            "items": [serializar_campania(item) for item in items],
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.get("/admin/campania-telefonica/<int:campania_id>/contactos/")
def listar_campania_contactos(campania_id: int):
    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        campaign = obtener_campania_del_usuario(campania_id, usuario_auth["id"])
        if campaign is None:
            return jsonify({"ok": False, "error": "Campania no encontrada para este usuario"}), 404

        page = max(1, request.args.get("page", default=1, type=int))
        page_size = min(max(1, request.args.get("page_size", default=20, type=int)), 100)
        estado = request.args.get("estado")
        usuario_asignado_id = request.args.get("usuario_asignado_id", type=int)
        q = (request.args.get("q") or "").strip().lower()

        query = (
            db.session.query(CampaniaContacto)
            .join(ContactoTelefonico, CampaniaContacto.contacto_id == ContactoTelefonico.id)
            .filter(CampaniaContacto.campania_id == campania_id)
        )

        if estado:
            query = query.filter(CampaniaContacto.estado == estado)
        if usuario_asignado_id is not None:
            query = query.filter(CampaniaContacto.usuario_asignado_id == usuario_asignado_id)
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    ContactoTelefonico.telefono_normalizado.ilike(like),
                    ContactoTelefonico.empresa.ilike(like),
                    ContactoTelefonico.ciudad.ilike(like),
                    ContactoTelefonico.email.ilike(like),
                )
            )

        total = query.count()
        items = (
            query.order_by(CampaniaContacto.fecha_creacion.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            .all()
        )

        return jsonify({
            "ok": True,
            "items": [serializar_campania_contacto(item) for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": (page * page_size) < total,
        }), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.patch("/admin/campania-telefonica/contacto/<int:campania_contacto_id>/estado/")
def actualizar_estado_campania_contacto(campania_contacto_id: int):
    payload = request.get_json(silent=True) or {}

    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        estado_nuevo = payload.get("estado")
        nota = payload.get("nota") if "nota" in payload else None

        if estado_nuevo is None and nota is None:
            return jsonify({"ok": False, "error": "Debes enviar un estado o una nota"}), 400

        if estado_nuevo is not None and estado_nuevo not in {item.value for item in CampaniaEstado}:
            return jsonify({"ok": False, "error": "Estado no soportado"}), 400

        relation_scope = (
            db.session.query(CampaniaContacto)
            .join(CampaniaTelefonica, CampaniaContacto.campania_id == CampaniaTelefonica.id)
            .filter(
                CampaniaContacto.id == campania_contacto_id,
                CampaniaTelefonica.usuario_creador_id == usuario_auth["id"],
            )
            .first()
        )
        if relation_scope is None:
            return jsonify({"ok": False, "error": "Contacto de campania no encontrado para este usuario"}), 404

        relation = importador_service.actualizar_estado_campania_contacto(
            campania_contacto_id=campania_contacto_id,
            estado_nuevo=estado_nuevo,
            usuario_id=usuario_auth["id"],
            nota=nota,
        )

        refreshed_relation = (
            db.session.query(CampaniaContacto)
            .join(ContactoTelefonico, CampaniaContacto.contacto_id == ContactoTelefonico.id)
            .filter(CampaniaContacto.id == relation.id)
            .first()
        )
        return jsonify({"ok": True, "item": serializar_campania_contacto(refreshed_relation)}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.get("/admin/campania-telefonica/contacto/<int:campania_contacto_id>/historial/")
def historial_campania_contacto(campania_contacto_id: int):
    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        items = (
            db.session.query(HistorialContacto)
            .join(CampaniaContacto, HistorialContacto.campania_contacto_id == CampaniaContacto.id)
            .join(CampaniaTelefonica, CampaniaContacto.campania_id == CampaniaTelefonica.id)
            .filter(HistorialContacto.campania_contacto_id == campania_contacto_id)
            .filter(CampaniaTelefonica.usuario_creador_id == usuario_auth["id"])
            .order_by(HistorialContacto.fecha.desc())
            .all()
        )
        return jsonify({"ok": True, "items": [serializar_historial(item) for item in items]}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass


@campania_telefonica.delete("/admin/campania-telefonica/<int:campania_id>/")
def eliminar_campania(campania_id: int):
    try:
        usuario_auth, error_response, status_code = resolver_usuario_importador_requerido()
        if error_response:
            return error_response, status_code

        campaign = obtener_campania_del_usuario(campania_id, usuario_auth["id"])
        if campaign is None:
            return jsonify({"ok": False, "error": "Campania no encontrada"}), 404

        contact_ids = [relation.contacto_id for relation in campaign.contactos]
        deleted_relations = len(campaign.contactos)

        db.session.delete(campaign)
        db.session.flush()

        deleted_contacts = 0
        if contact_ids:
            orphan_contacts = (
                db.session.query(ContactoTelefonico)
                .outerjoin(CampaniaContacto, ContactoTelefonico.id == CampaniaContacto.contacto_id)
                .filter(
                    ContactoTelefonico.id.in_(contact_ids),
                    CampaniaContacto.id.is_(None),
                )
                .all()
            )

            deleted_contacts = len(orphan_contacts)
            for contact in orphan_contacts:
                db.session.delete(contact)

        db.session.commit()

        return jsonify({
            "ok": True,
            "campania_id": campania_id,
            "deleted_relations": deleted_relations,
            "deleted_contacts": deleted_contacts,
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        try:
            db.session.close()
        except Exception:
            pass