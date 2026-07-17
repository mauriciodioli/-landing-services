from datetime import datetime

from extensions import db
from models.campania_telefonica import CampaniaEstado


class CampaniaContacto(db.Model):
    __tablename__ = "campania_contacto"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campania_id = db.Column(
        db.Integer,
        db.ForeignKey("campania_telefonica.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contacto_id = db.Column(
        db.Integer,
        db.ForeignKey("contacto_telefonico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_asignado_id = db.Column(db.Integer, nullable=True, index=True)
    estado = db.Column(
        db.String(20),
        nullable=False,
        default=CampaniaEstado.NUEVO.value,
        index=True,
    )
    cantidad_intentos = db.Column(db.Integer, nullable=False, default=0)
    fecha_ultimo_contacto = db.Column(db.DateTime, nullable=True)
    observacion = db.Column(db.Text, nullable=True)
    eliminado = db.Column(db.Boolean, nullable=False, default=False)
    exitoso = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    campania = db.relationship("CampaniaTelefonica", back_populates="contactos")
    contacto = db.relationship("ContactoTelefonico", back_populates="campanias")
    historiales = db.relationship(
        "HistorialContacto",
        back_populates="campania_contacto",
        cascade="all, delete-orphan",
        lazy=True,
    )

    __table_args__ = (
        db.UniqueConstraint("campania_id", "contacto_id", name="uq_campania_contacto"),
    )

    def __repr__(self):
        return (
            f"<CampaniaContacto id={self.id} campania_id={self.campania_id} "
            f"contacto_id={self.contacto_id} estado={self.estado}>"
        )