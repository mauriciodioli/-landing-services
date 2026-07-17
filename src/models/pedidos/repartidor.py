# models/pedidos/repartidor.py

from flask_marshmallow import Marshmallow
from flask import Blueprint
from utils.db import db
from sqlalchemy import inspect
from datetime import datetime

# ✅ Importar Usuario del archivo correcto
from models.usuario import Usuario

ma = Marshmallow()
repartidor = Blueprint('repartidor', __name__)


class Repartidor(db.Model):
    __tablename__ = 'repartidor'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # ✅ Relación con Usuario (user_id apunta a usuarios.id)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id', ondelete='SET NULL'),
        nullable=True
    )

    activo = db.Column(db.Boolean, nullable=False, default=True)
    disponible = db.Column(db.Boolean, nullable=False, default=True)
    nombre = db.Column(db.String(255), nullable=False)
    apellido = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    vehiculo = db.Column(db.String(50), nullable=True)
    patente = db.Column(db.String(50), nullable=True)
    latitud = db.Column(db.Float, nullable=True)
    longitud = db.Column(db.Float, nullable=True)
    ultima_actualizacion_gps = db.Column(db.DateTime, nullable=True)
    radio_trabajo_km = db.Column(db.Float, default=10.0)
    pedidos_activos = db.Column(db.Integer, default=0)
    puntuacion = db.Column(db.Float, default=5.0)
    total_entregas = db.Column(db.Integer, default=0)
    total_cancelaciones = db.Column(db.Integer, default=0)
    fecha_alta = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_baja = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    # ✅ Relación con Usuario (usando el modelo importado)
    usuario = db.relationship(
        "Usuario",
        backref="repartidor",
        lazy='joined',
        foreign_keys=[user_id]
    )

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"<Repartidor {self.nombre} ({self.telefono})>"

    @classmethod
    def crear_tabla_repartidor(cls):
        insp = inspect(db.engine)
        if not insp.has_table("repartidor"):
            db.create_all()


class RepartidorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Repartidor
        load_instance = True
        sqla_session = db.session
        include_fk = True
        fields = (
            "id",
            "user_id",
            "activo",
            "disponible",
            "nombre",
            "apellido",
            "telefono",
            "email",
            "vehiculo",
            "patente",
            "latitud",
            "longitud",
            "ultima_actualizacion_gps",
            "radio_trabajo_km",
            "pedidos_activos",
            "puntuacion",
            "total_entregas",
            "total_cancelaciones",
            "fecha_alta",
            "fecha_baja",
            "observaciones"
        )


repartidor_schema = RepartidorSchema()
repartidores_schema = RepartidorSchema(many=True)