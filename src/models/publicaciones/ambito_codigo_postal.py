from flask_marshmallow import Marshmallow
from flask import Blueprint
from utils.db import db
from sqlalchemy import inspect, Column, Integer, String


ma = Marshmallow()

ambito_codigo_postal = Blueprint('ambito_codigo_postal', __name__)


class AmbitoCodigoPostal(db.Model):
    __tablename__ = 'ambito_codigo_postal'

    # Columnas de la tabla
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)   
    estado = db.Column(db.String(500), nullable=True)
    codigo_postal_id = db.Column(db.Integer, db.ForeignKey('codigo_postal.id'), nullable=False)
    ambito_id = db.Column(db.Integer, db.ForeignKey('ambitos.id'), nullable=False)
    # Constructor
    def __init__(self, ambito_id, codigo_postal_id, estado=None):
        self.ambito_id = ambito_id
        self.codigo_postal_id = codigo_postal_id
        self.estado = estado

    def __repr__(self):
        return f"AmbitoCodigoPostal(id={self.id}, ambito_id={self.ambito_id}, codigo_postal_id={self.codigo_postal_id}, estado={self.estado})"

    @classmethod
    def crear_tabla_ambitoCodigoPostal(self):
        # Verificar si la tabla existe antes de crearla
        insp = inspect(db.engine) 
        if not insp.has_table("ambito_codigo_postal"):
            db.create_all()




# Schema de Marshmallow para serialización
class MerShema(ma.Schema):
    class Meta:       
        fields = ("id", "ambito_id", "codigo_postal_id","estado" )  # Campos a serializar