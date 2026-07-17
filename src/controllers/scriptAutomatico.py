import pandas as pd
from datetime import date

# Función simulada para obtener productos en tendencia (mock, normalmente vendría de scraping/API)
def obtener_productos_tendencia():
    productos = [
        {
            "producto": "Freidora de aire digital",
            "categoría": "Cocina",
            "país": "Argentina",
            "fuente": "Google Trends Argentina",
            "motivo_tendencia": "Alta búsqueda por cocina saludable",
            "motivo_tendencia_extendido": "Según Google Trends Argentina, ha habido un aumento significativo en las búsquedas relacionadas con freidoras sin aceite.",
            "descripcion": "Freidora sin aceite con control digital, ideal para cocinar de forma saludable.",
            "precio_amazon": 95,
            "precio_ebay": 90,
            "precio_aliexpress": 80,
            "precio_venta_sugerido": 129,
            "imagen": "https://m.media-amazon.com/images/I/71Z1BmKjHHL._AC_SX679_.jpg",
        },
        {
            "producto": "Reloj inteligente deportivo",
            "categoría": "Tecnología",
            "país": "Argentina",
            "fuente": "Amazon Argentina",
            "motivo_tendencia": "Popularidad en fitness y salud",
            "motivo_tendencia_extendido": "Producto destacado en Amazon por su utilidad en monitoreo de actividad física y salud.",
            "descripcion": "Smartwatch con monitoreo cardíaco y GPS integrado.",
            "precio_amazon": 75,
            "precio_ebay": 70,
            "precio_aliexpress": 50,
            "precio_venta_sugerido": 99,
            "imagen": "https://m.media-amazon.com/images/I/71wKe2YnnFL._AC_SX679_.jpg",
        },
        {
            "producto": "Mochila antirrobo urbana",
            "categoría": "Moda",
            "país": "Argentina",
            "fuente": "Tiendanube Trends",
            "motivo_tendencia": "Seguridad y estilo para viajeros urbanos",
            "motivo_tendencia_extendido": "Tiendanube reporta un aumento en ventas de mochilas antirrobo por su diseño moderno y funcionalidad.",
            "descripcion": "Mochila con cierre oculto, compartimento para laptop y puerto USB.",
            "precio_amazon": 45,
            "precio_ebay": 40,
            "precio_aliexpress": 30,
            "precio_venta_sugerido": 69,
            "imagen": "https://m.media-amazon.com/images/I/71IHkxN0etL._AC_SX679_.jpg",
        },
    ]

    # Cálculo automático de margen y fechas + links
    for p in productos:
        p["margen_estimado"] = p["precio_venta_sugerido"] - min(p["precio_amazon"], p["precio_ebay"], p["precio_aliexpress"])
        p["fecha"] = str(date.today())
        p["búsqueda_amazon"] = f"https://www.amazon.com/s?k={p['producto'].replace(' ', '+')}"
        p["búsqueda_ebay"] = f"https://www.ebay.com/sch/i.html?_nkw={p['producto'].replace(' ', '+')}"
        p["búsqueda_aliexpress"] = f"https://www.aliexpress.com/wholesale?SearchText={p['producto'].replace(' ', '+')}"

    return productos

# Generar DataFrame
productos = obtener_productos_tendencia()
df = pd.DataFrame(productos)

# Mostrar al usuario
import ace_tools as tools; tools.display_dataframe_to_user(name="Productos Automatizados - Base Python", dataframe=df)
