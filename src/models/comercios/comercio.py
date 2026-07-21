from flask_marshmallow import Marshmallow
from flask import Blueprint
from utils.db import db
from sqlalchemy import inspect
from datetime import datetime

from models.usuario import Usuario

ma = Marshmallow()
comercios = Blueprint('comercios', __name__)


class Comercio(db.Model):
    __tablename__ = 'comercios'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    nombre = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    direccion = db.Column(db.String(500), nullable=True)
    latitud = db.Column(db.Float, nullable=True)
    longitud = db.Column(db.Float, nullable=True)
    ambito = db.Column(db.String(100), nullable=True)
    categoria_id = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_alta = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    usuario = db.relationship(
        "Usuario",
        backref="comercios",
        lazy='joined',
        foreign_keys=[user_id]
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"<Comercio {self.nombre} ({self.email or self.telefono})>"

    @classmethod
    def crear_tabla_comercios(cls):
        insp = inspect(db.engine)
        if not insp.has_table("comercios"):
            db.create_all()


class ComercioSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Comercio
        load_instance = True
        sqla_session = db.session
        include_fk = True
        fields = (
            'id', 'user_id', 'nombre', 'telefono', 'email', 'direccion', 'latitud', 'longitud',
            'ambito', 'categoria_id', 'activo', 'fecha_alta', 'fecha_baja', 'observaciones'
        )


comercio_schema = ComercioSchema()
comercios_schema = ComercioSchema(many=True)
