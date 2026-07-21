from datetime import datetime
from enum import Enum

from sqlalchemy import inspect, text

from extensions import db


class CampaniaEstado(str, Enum):
    NUEVO = "NUEVO"
    LLAMADO = "LLAMADO"
    PENDIENTE = "PENDIENTE"
    EXITOSO = "EXITOSO"
    ELIMINADO = "ELIMINADO"
    NO_RESPONDE = "NO_RESPONDE"


class CampaniaTelefonica(db.Model):
    __tablename__ = "campania_telefonica"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_creador_id = db.Column(db.Integer, nullable=True, index=True)
    nombre = db.Column(db.String(255), nullable=False)
    sheet_id = db.Column(db.String(255), nullable=True)
    sheet_name = db.Column(db.String(255), nullable=False)
    sheet_tab = db.Column(db.String(255), nullable=True)
    estado = db.Column(
        db.String(20),
        nullable=False,
        default=CampaniaEstado.NUEVO.value,
        index=True,
    )
    total_registros = db.Column(db.Integer, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    contactos = db.relationship(
        "CampaniaContacto",
        back_populates="campania",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return f"<CampaniaTelefonica id={self.id} nombre='{self.nombre}' estado={self.estado}>"


def ensure_campania_telefonica_schema(engine):
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "campania_telefonica" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("campania_telefonica")}
    if "sheet_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE campania_telefonica ADD COLUMN sheet_id VARCHAR(255) NULL"))