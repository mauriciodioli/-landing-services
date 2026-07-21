from datetime import datetime

from extensions import db
from models.campania_telefonica import CampaniaEstado


class ContactoTelefonico(db.Model):
    __tablename__ = "contacto_telefonico"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    telefono_normalizado = db.Column(db.String(50), unique=True, nullable=False, index=True)
    telefono_original = db.Column(db.String(100), nullable=True)
    empresa = db.Column(db.String(255), nullable=True)
    ciudad = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    web = db.Column(db.String(255), nullable=True)
    json_data = db.Column(db.JSON, nullable=False)
    estado_global = db.Column(
        db.String(20),
        nullable=False,
        default=CampaniaEstado.NUEVO.value,
        index=True,
    )
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    campanias = db.relationship(
        "CampaniaContacto",
        back_populates="contacto",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self):
        return (
            f"<ContactoTelefonico id={self.id} telefono_normalizado={self.telefono_normalizado} "
            f"estado_global={self.estado_global}>"
        )