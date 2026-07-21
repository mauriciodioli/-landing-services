from datetime import datetime

from extensions import db


class HistorialContacto(db.Model):
    __tablename__ = "historial_contacto"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campania_contacto_id = db.Column(
        db.Integer,
        db.ForeignKey("campania_contacto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id = db.Column(db.Integer, nullable=True, index=True)
    accion = db.Column(db.String(100), nullable=False)
    estado_anterior = db.Column(db.String(20), nullable=True)
    estado_nuevo = db.Column(db.String(20), nullable=True)
    nota = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    campania_contacto = db.relationship("CampaniaContacto", back_populates="historiales")

    def __repr__(self):
        return (
            f"<HistorialContacto id={self.id} campania_contacto_id={self.campania_contacto_id} "
            f"accion={self.accion}>"
        )