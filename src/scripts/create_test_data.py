#!/usr/bin/env python3
"""Script de utilidad para crear datos de prueba: usuario, comercio, publicacion y pedido."""
from datetime import datetime
import sys

# Importar la app para inicializar extensiones
from app import app
from utils.db_session import get_db_session
from models.usuario import Usuario
from models.comercios.comercio import Comercio
from models.publicaciones.publicaciones import Publicacion
from models.pedidos.pedidoEntregaPago import PedidoEntregaPago
from extensions import db


def main():
    with app.app_context():
        # Asegurarnos de que la tabla 'comercios' exista
        Comercio.__table__.create(bind=db.engine, checkfirst=True)

        with get_db_session() as db_session:
            # 1) Crear usuario si no existe
            email = 'test_comercio@example.com'
            usuario = db_session.query(Usuario).filter_by(correo_electronico=email).first()
            if not usuario:
                usuario = Usuario(correo_electronico=email, password=None)
                db_session.add(usuario)
                db_session.flush()
                print('Usuario creado id=', usuario.id)
            else:
                print('Usuario ya existe id=', usuario.id)

            # 2) Crear comercio
            comercio = db_session.query(Comercio).filter_by(user_id=usuario.id).first()
            if not comercio:
                comercio = Comercio(
                    user_id=usuario.id,
                    nombre='Local Prueba',
                    telefono='+34123456789',
                    email=email,
                    direccion='Calle Falsa 123',
                    latitud=42.0,
                    longitud=12.0,
                    ambito='Nacional',
                    categoria_id=1,
                    activo=True,
                    fecha_alta=datetime.now()
                )
                db_session.add(comercio)
                db_session.flush()
                print('Comercio creado id=', comercio.id)
            else:
                print('Comercio ya existe id=', comercio.id)

            # 3) Crear publicacion
            publicacion = db_session.query(Publicacion).filter_by(user_id=usuario.id, titulo='publicacion_prueba_test').first()
            if not publicacion:
                publicacion = Publicacion(
                    user_id=usuario.id,
                    titulo='publicacion_prueba_test',
                    texto='Texto de prueba',
                    ambito='Nacional',
                    categoria_id=1,
                    correo_electronico=email,
                    descripcion='Desc prueba',
                    color_texto='black',
                    color_titulo='black',
                    fecha_creacion=datetime.now(),
                    estado='activo',
                    codigoPostal='12345',
                    pagoOnline=True,
                    afiliado_link=''
                )
                db_session.add(publicacion)
                db_session.flush()
                print('Publicacion creada id=', publicacion.id)
            else:
                print('Publicacion ya existe id=', publicacion.id)

            # 4) Crear pedido
            pedido = db_session.query(PedidoEntregaPago).filter_by(publicacion_id=publicacion.id, user_id=usuario.id).first()
            if not pedido:
                pedido = PedidoEntregaPago(user_id=usuario.id, publicacion_id=publicacion.id, cantidad=1)
                # Campos requeridos
                pedido.cliente_id = usuario.id
                pedido.cluster_id = 0
                pedido.precio_venta = 9.99
                pedido.estado = 'pendiente'
                pedido.lugar_entrega = 'Calle Falsa 123'
                pedido.nombreCliente = 'Cliente Test'
                pedido.apellidoCliente = 'Apellido'
                pedido.telefonoCliente = '+34123456789'
                # fecha_creacion puede no estar en el modelo, asignar directamente
                try:
                    pedido.fecha_creacion = datetime.now()
                except Exception:
                    pass
                db_session.add(pedido)
                db_session.flush()
                print('Pedido creado id=', pedido.id)
            else:
                print('Pedido ya existe id=', pedido.id)

            print('\nHecho. Usa el ID del comercio para filtrar: comercio_id=', comercio.id)


if __name__ == '__main__':
    main()
