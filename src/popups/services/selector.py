from extensions import db
from models.popupsm.popup import Popup
from sqlalchemy.exc import SQLAlchemyError
from models.publicaciones.publicaciones import Publicacion
from models.publicaciones.estado_publi_usu import Estado_publi_usu
from models.publicaciones.publicacion_imagen_video import Public_imagen_video
from models.usuarioRegion import UsuarioRegion
from models.usuarioUbicacion import UsuarioUbicacion
from models.usuarioPublicacionUbicacion import UsuarioPublicacionUbicacion
from models.publicaciones.ambitoCategoria import AmbitoCategoria
from models.publicaciones.categoriaPublicacion import CategoriaPublicacion
from models.publicaciones.publicacionCodigoPostal import PublicacionCodigoPostal
from models.publicaciones.ambitos import Ambitos
from models.publicaciones.ambito_usuario import Ambito_usuario
from models.publicaciones.ambitoCategoriaRelation import AmbitoCategoriaRelation
from models.categoriaCodigoPostal import CategoriaCodigoPostal
import controllers.publicaciones as publicaciones

def seleccionar_popup(dominio=None, categoria=None, lang=None, cp=None):
    q = db.session.query(Popup).filter(Popup.estado == "activo")

    # Filtros suaves (permiten NULL como comodín)
    if lang:
        q = q.filter((Popup.idioma == lang) | (Popup.idioma.is_(None)))
    if cp:
        q = q.filter((Popup.codigo_postal == cp) | (Popup.codigo_postal.is_(None)))

    # Ambito (dominio)
    amb_id = None
    if dominio:
        if str(dominio).isdigit():
            amb = publicaciones.machear_ambito_id(dominio, lang)
        else:
            amb = publicaciones.machear_ambito(dominio, lang)
        # puede venir un obj con .id o directamente un int
        amb_id = getattr(amb, "id", amb)
        if amb_id is not None:
            q = q.filter((Popup.dominio_id == amb_id) | (Popup.dominio_id.is_(None)))

    # Categoría (usa amb_id si existe)
    if categoria:
        if str(dominio).isdigit():
           cat = publicaciones.machear_ambitoCategoria_id(categoria, lang)
        else:
          cat = publicaciones.machear_ambitoCategoria(categoria, lang, amb_id)
        cat_id = getattr(cat, "id", cat)
        if cat_id is not None:
            q = q.filter((Popup.categoria_id == cat_id) | (Popup.categoria_id.is_(None)))

    # Orden: primero prioridad, luego más nuevo
    p = q.order_by(Popup.prioritario.desc(), Popup.fecha_creacion.desc()).first()
    if not p:
        return None

    return {
        "id": p.id,
        "title": p.titulo or "",
        "image": p.imagen_url,
        "width": p.medida_ancho or 400,
        "height": p.medida_alto or 600,
        # destino: primero link (click), luego micrositio como fallback
        "href": p.link or p.micrositio_url or "#",
    }









def _serialize_popup(p):
    return {
        "id": p.id,
        "title": p.titulo or "",
        "image": p.imagen_url,
        "width": p.medida_ancho or 400,
        "height": p.medida_alto or 600,
        "href": p.link or p.micrositio_url or "#",
    }

def seleccionar_popups(dominio=None, categoria=None, lang=None, cp=None, limit=None):
    q = db.session.query(Popup).filter(Popup.estado == "activo")

    # comodines: idioma y CP permiten NULL
    if lang:
        q = q.filter((Popup.idioma == lang) | (Popup.idioma.is_(None)))
    if cp:
        q = q.filter((Popup.codigo_postal == cp) | (Popup.codigo_postal.is_(None)))

    # Ámbito (dominio)
    amb_id = None
    if dominio:
        if str(dominio).isdigit():
            amb = publicaciones.machear_ambito_id(dominio, lang)
        else:
            amb = publicaciones.machear_ambito(dominio, lang)
        amb_id = getattr(amb, "id", amb)
        if amb_id is not None:
            q = q.filter((Popup.dominio_id == amb_id) | (Popup.dominio_id.is_(None)))

    # Categoría (usar amb_id si existe)  **FIX**: usar 'categoria' acá
    if categoria:
        if str(categoria).isdigit():
            cat = publicaciones.machear_ambitoCategoria_id(categoria, lang)
        else:
            cat = publicaciones.machear_ambitoCategoria(categoria, lang, amb_id)
        cat_id = getattr(cat, "id", cat)
        if cat_id is not None:
            q = q.filter((Popup.categoria_id == cat_id) | (Popup.categoria_id.is_(None)))

    # Orden: prioridad desc, luego más nuevo
    q = q.order_by(Popup.prioritario.desc(), Popup.fecha_creacion.desc())

    rows = q.limit(limit).all() if limit else q.all()
    return [_serialize_popup(p) for p in rows]






# src/popups/services/selector.py
def seleccionar_popup_test(dominio=None, categoria=None, lang=None, cp=None):
    # TODO: reemplazar por query real cuando tengas el modelo
    return {
        "id": 1,
        "title": "Promo Reparación",
        "image": "data:image/jpeg;base64,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",
        "width": 600,
        "height": 200,
        "href": "https://dpia.site",
    }
