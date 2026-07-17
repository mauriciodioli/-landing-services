# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_marshmallow import Marshmallow
from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from utils.db import db
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

ma = Marshmallow()
popup = Blueprint("popup", __name__)

class Popup(db.Model):
    __tablename__ = "popup"
    __table_args__ = {'extend_existing': True}  # evita choque si se carga dos veces

    id              = db.Column(db.Integer, primary_key=True)
    titulo          = db.Column(db.String(200))
    imagen_url      = db.Column(db.String(500), nullable=False)
    micrositio_url  = db.Column(db.String(500))          # opcional
    link            = db.Column(db.String(500))          # destino click
    idioma          = db.Column(db.String(10))
    codigo_postal   = db.Column(db.String(20))
    dominio_id      = db.Column(db.Integer)              # FK → Ambitos (si aplica)
    categoria_id    = db.Column(db.Integer)              # FK → Categoria
    publicacion_id  = db.Column(db.Integer)              # FK → Publicacion
    user_id         = db.Column(db.Integer)              # FK → Usuario creador
    prioritario     = db.Column(db.Integer, default=0, nullable=False)
    estado          = db.Column(db.String(20), default="activo", nullable=False)
    medida_ancho    = db.Column(db.Integer, default=400, nullable=False)
    medida_alto     = db.Column(db.Integer, default=600, nullable=False)
    fecha_creacion  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(
        self,
        titulo: str,
        imagen_url: str,
        micrositio_url: str = None,
        link: str = None,
        idioma: str = None,
        codigo_postal: str = None,
        dominio_id: int = None,
        categoria_id: int = None,
        publicacion_id: int = None,
        user_id: int = None,
        prioritario: int = 0,
        estado: str = "activo",
        medida_ancho: int = 400,
        medida_alto: int = 600,
    ):
        self.titulo = titulo
        self.imagen_url = imagen_url
        self.micrositio_url = micrositio_url
        self.link = link
        self.idioma = idioma
        self.codigo_postal = codigo_postal
        self.dominio_id = dominio_id
        self.categoria_id = categoria_id
        self.publicacion_id = publicacion_id
        self.user_id = user_id
        self.prioritario = prioritario
        self.estado = estado
        self.medida_ancho = medida_ancho
        self.medida_alto = medida_alto

    def __repr__(self):
        return (
            f"<Popup id={self.id} titulo='{self.titulo}' "
            f"cp={self.codigo_postal} lang={self.idioma} "
            f"prio={self.prioritario} estado={self.estado} "
            f"dom={self.dominio_id} cat={self.categoria_id} "
            f"pub={self.publicacion_id} user={self.user_id}>"
        )

    @classmethod
    def crear_tabla_popup(cls):
        insp = inspect(db.engine)
        if not insp.has_table(cls.__tablename__):
            db.create_all()


# -------- Marshmallow (usar AutoSchema) --------
class PopupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Popup
        sqla_session = db.session
        load_instance = True
        include_fk = True

popup_schema = PopupSchema()
popups_schema = PopupSchema(many=True)

# ---------- Helper: mapear payload del form a modelo ----------
def mapear_form_a_modelo(data: dict) -> dict:
    """
    Front envía (nombres de formulario):
      dominio, categoria, lang, cp, title, href, image, width, height, prioritario, activo
    Modelo espera:
      titulo, imagen_url, link, idioma, codigo_postal, medida_ancho, medida_alto, ...
    """
    return {
        # campos de negocio
        "titulo":         data.get("title") or data.get("titulo"),
        "imagen_url":     data.get("image") or data.get("imagen_url"),
        "link":           data.get("href")  or data.get("link"),
        "micrositio_url": data.get("micrositio_url"),  # opcional

        # segmentación
        "idioma":         data.get("lang") or data.get("idioma"),
        "codigo_postal":  data.get("cp")   or data.get("codigo_postal"),

        # FKs (si ya vienen por id)
        "dominio_id":     data.get("dominio_id"),
        "categoria_id":   data.get("categoria_id"),
        "publicacion_id": data.get("publicacion_id"),
        "user_id":        data.get("user_id"),

        # otros
        "prioritario":    int(data.get("prioritario") or 0),
        "estado":         ("activo" if (str(data.get("activo")) in ("1", "true", "True")) else data.get("estado")) or "activo",
        "medida_ancho":   int(data.get("width")  or data.get("medida_ancho") or 400),
        "medida_alto":    int(data.get("height") or data.get("medida_alto") or 600),

        # guardo texto crudo por si tengo que resolver FKs
        "ambito":         data.get("dominio")   or data.get("ambito"),
        "categoria":      data.get("categoria"),
        
        # pasa el email para validación (NO es columna del popup)
        "email":          data.get("email") or data.get("correo_electronico"),
    }