from flask_marshmallow import Marshmallow
from flask import Blueprint
from utils.db import db
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

ma = Marshmallow()

pedidoEntregaPago = Blueprint('pedidoEntregaPago', __name__)

class PedidoEntregaPago(db.Model):
    __tablename__ = 'pedidoEntregaPago'
    
    # Atributos del modelo Pedido
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    cliente_id = db.Column(db.Integer, nullable=False)
    cluster_id = db.Column(db.Integer, nullable=False)
    publicacion_id = db.Column(db.Integer, nullable=False)
    fecha_entrega = db.Column(DateTime, nullable=True)  # Fecha estimada de entrega
    fecha_consulta = db.Column(DateTime, nullable=True)  # Fecha de consulta (si aplica)
    lugar_entrega = db.Column(String(255), nullable=True)  # Dirección de entrega
    
    cantidad = db.Column(Integer, nullable=False, default=1)  # Cantidad pedida
    precio_venta = db.Column(Float, nullable=True)  # Precio de venta
    consulta = db.Column(Text, nullable=True)  # Texto de consulta del cliente
    estado = db.Column(String(50), nullable=True)  # Por ejemplo, "pendiente", "completado", "cancelado"
   
    asignado_a = db.Column(String(255), nullable=True)  # Persona o equipo asignado al pedido
    tamaño = db.Column(String(50), nullable=True)  # Tamaño del producto (si aplica)
    pais = db.Column(String(100), nullable=True)  # País de entrega
    provincia = db.Column(String(100), nullable=True)  # Provincia o estado
    region = db.Column(String(100), nullable=True)  # Región (si aplica)
    sexo = db.Column(String(20), nullable=True)  # Información del cliente, si es relevante
    
    nombreCliente = db.Column(String(255), nullable=True)
    apellidoCliente = db.Column(String(255), nullable=True)
    emailCliente = db.Column(String(255), nullable=True)
    telefonoCliente = db.Column(String(255), nullable=True)
    comentarioCliente = db.Column(Text, nullable=True)
    ambito = db.Column(String(50), nullable=True)  # Por ejemplo, "nacional" o "internacional"
    pedido_data_json = db.Column(Text, nullable=True)
    
    # Constructor
    def __init__(self, user_id, publicacion_id, **kwargs):
        self.user_id = user_id
        self.publicacion_id = publicacion_id
        for key, value in kwargs.items():
            setattr(self, key, value)

    # Representación para debugging
    def __repr__(self):
        return (
            f"<Pedido(id={self.id}, user_id={self.user_id}, publicacion_id={self.publicacion_id}, "
            f"estado={self.estado}, fecha_entrega={self.fecha_entrega})>"
        )

# Esquema para serialización
class PedidoEntregaPagoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PedidoEntregaPago
        fields = (
            "id", "user_id", "cliente_id", "publicacion_id", "ambito", "estado",
            "fecha_entrega", "lugar_entrega", "cantidad", "precio_venta",
            "consulta", "asignado_a", "tamaño", "pais", "provincia", "region", "sexo",
            "nombreCliente", "apellidoCliente", "emailCliente", "telefonoCliente", "comentarioCliente"
        )

# Instancias del esquema
pedidoEntregaPagoschema = PedidoEntregaPagoSchema()
pedidoEntregaPagoschema = PedidoEntregaPagoSchema(many=True)
