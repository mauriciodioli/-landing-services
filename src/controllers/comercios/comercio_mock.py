from datetime import datetime, timedelta
import random
from models.pedidos.pedidoEntregaPago import PedidoEntregaPago
from utils.db_session import get_db_session
def generar_datos_mock_comercio():
    nombres = ["Lucas", "Sofía", "Mateo", "Valentina", "Diego", "Elena"]
    apellidos = ["Rossi", "Bianchi", "Ferrari", "Marino", "Ricci", "Bruno"]
    direcciones = ["Corso Garibaldi 45, Spoleto", "Piazza del Duomo 2, Spoleto", "Via dell'Anfiteatro 12, Spoleto"]
    estados = ["pendiente", "preparacion", "listo", "enviado", "entregado"] # Quitamos 'cancelado' temporalmente por si pide fecha_cancelacion obligatoria

    with get_db_session() as session:
        ahora = datetime.now()

        for i in range(12):
            estado_asignado = random.choice(estados)
            precio = round(random.uniform(15000.0, 45000.0), 2) 
            
            nuevo_pedido = PedidoEntregaPago()
            nuevo_pedido.estado = estado_asignado
            nuevo_pedido.nombreCliente = random.choice(nombres)
            nuevo_pedido.apellidoCliente = random.choice(apellidos)
            nuevo_pedido.telefonoCliente = f"+39333{random.randint(1000000, 9999999)}"
            nuevo_pedido.lugar_entrega = random.choice(direcciones)
            nuevo_pedido.precio_venta = precio
            nuevo_pedido.fecha_creacion = ahora - timedelta(hours=random.randint(1, 5))
            
            # Campos opcionales inicializados de manera segura
            if estado_asignado in ["enviado", "entregado"]:
                nuevo_pedido.fecha_envio = ahora - timedelta(minutes=30)
                nuevo_pedido.repartidor_id = 4
            if estado_asignado == "entregado":
                nuevo_pedido.fecha_entrega = ahora - timedelta(minutes=5)

            session.add(nuevo_pedido)
        
        session.flush()
    return {"success": True, "message": "12 Pedidos Mock creados exitosamente."}