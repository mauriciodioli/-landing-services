from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, jsonify
from extensions import db

from models.usuario import Usuario
import requests
from sqlalchemy.exc import SQLAlchemyError
from models.publicaciones.publicaciones import Publicacion
from models.publicaciones.estado_publi_usu import Estado_publi_usu
from models.publicaciones.publicacion_imagen_video import Public_imagen_video
from models.usuarioRegion import UsuarioRegion
from models.usuarioUbicacion import UsuarioUbicacion
from models.usuarioPublicacionUbicacion import UsuarioPublicacionUbicacion
from models.publicaciones.ambitoCategoria import AmbitoCategoria
from models.publicaciones.categoriaPublicacion import CategoriaPublicacion
from models.publicaciones.ambitos import Ambitos
from models.publicaciones.ambitoCategoriaRelation import AmbitoCategoriaRelation
from models.image import Image
from models.video import Video
import random
import pandas as pd  
from typing import List, Dict, Any
import sys
import os
import re
import json
import math
from datetime import datetime
from werkzeug.utils import secure_filename


filtro_publicacion = Blueprint('filtro_publicacion', __name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
BASE_STATIC_DOWNLOADS = os.path.join(BASE_DIR, "src", "static", "downloads")
SIZE_TAG = re.compile(r'_[A-Z]{2}_[A-Z0-9]+_\.(jpg|png)$', re.IGNORECASE)
# 1. Calcula la ruta al directorio raíz de tu proyecto (dos niveles arriba de este archivo)

MARCAS_RESTRINGIDAS = ["adidas", "nike", "apple", "samsung", "sony", "puma", "lenovo", "huawei", "lg"]



# Completar la publicación con datos del sheet y base de datos


def _to_float(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r'(\d+[.,]?\d*)', str(val))
    return float(m.group(1).replace(',', '.')) if m else None

def _to_int(val):
    if val is None or val == "":
        return 0
    if isinstance(val, int):
        return val
    m = re.search(r'(\d[\d.,]*)', str(val))
    return int(m.group(1).replace('.', '').replace(',', '')) if m else 0

def filtro_publicaciones(items: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    """
    - Guarda ítems sin rating siempre que tengan precio > 0.
    - Si hay rating, aplica filtros mínimos y pondera:
        score = precio / (rating * log(reviews + 1))
      (menor score = mejor)
    - Devuelve hasta k ítems: primero los ponderados por score, luego
      los sin rating ordenados por menor precio.
    """
    con_rating = []
    sin_rating = []
    descartados = []

    for d in items:
        precio = _to_float(d.get("precio"))
        if not precio or precio <= 0:
            d["__motivo_descartado"] = "Precio no válido"
            descartados.append(d)
            continue

        rating = _to_float(d.get("rating"))
        reviews = _to_int(d.get("reviews"))

        if rating is None:
            # Guardar SIN rating (ordenaremos por menor precio)
            d["__score_fallback"] = precio
            sin_rating.append(d)
            continue

        # Con rating: aplicar umbrales mínimos
        if rating < 4.4:
            d["__motivo_descartado"] = f"Rating bajo ({rating})"
            descartados.append(d)
            continue
        if reviews < 50:
            d["__motivo_descartado"] = f"Pocas reviews ({reviews})"
            descartados.append(d)
            continue

        # Ponderación
        score = precio / (rating * math.log(reviews + 1))
        d["__score"] = score
        d["__rating_val"] = rating
        d["__reviews_val"] = reviews
        con_rating.append(d)

    # Orden y selección
    con_rating.sort(key=lambda x: x["__score"])
    sin_rating.sort(key=lambda x: x["__score_fallback"])

    top = (con_rating + sin_rating)[:k]

    # Si no quedó nada elegible, devolvemos 1 descartado como placeholder
    if not top:
        return [{
            "titulo": d.get("titulo", "Sin título"),
            "descartado": True,
            "motivo": d.get("__motivo_descartado", "No elegible")
        } for d in descartados[:1]]

    return top







# ──────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────


def armar_publicaciones_validas_match_scrping_sheet(
    filas_validas: List[Dict],
    resultados_globales: List[Dict],
    sheet_name: str,
    token: str,
) -> List[Dict]:
    """
    Copia cada fila del Sheet y modifica:
      · pais_scrapeado
      · items_filtrados (con campos imagen1 … imagen6 completos)
    """
      
    por_kw = {r["producto"]: {"items": r["items"], "row_index": r.get("row_index")} for r in resultados_globales}

    publicaciones: List[Dict] = []

    for fila in filas_validas:
       
        kw = fila["Producto"]
        datos = por_kw.get(kw, {})
        raw_items = datos.get("items", [])
        row_index = fila.get("row_index")
        print(f"[DEBUG] armar_publicaciones_validas_match_scrping_sheet Ruta al archivo JSON principal: {kw}", flush=True)
        top3 = filtro_publicaciones(raw_items, 3)
        for d in top3:
            print("DEBUG ORIGINAL:", json.dumps(d, indent=2, ensure_ascii=False))

        print(f"[DEBUG] armar_publicaciones_validas_match_scrping_shee :filtro_publicaciones()", flush=True)
  
        for it in top3:
            dominio = (
                it.get("url", "").split("amazon.")[1][:2]
                if "amazon." in it.get("url", "")
                else "com"
            )
            galeria = []
            galeria = obtener_galeria(it.get("asin", ""), token, dominio)
            print(f"[DEBUG] armar_publicaciones_validas_match_scrping_shee :obtener_galeria()", flush=True)
  
            def _url(v):
                return v.get("imageUrl", "") if isinstance(v, dict) else (v or "")

            fotos_raw = [it.get("imagen", "")] + galeria
            fotos = [_url(u) for u in fotos_raw]           # normaliza todo
            fotos = (fotos + [""] * 6)[:6]
            for i in range(6):
                it[f"imagen{i+1}"] = fotos[i]
            it["precio_venta_sugerido"] = it.get("precio", 0.0)


        # Copia la fila de la hoja y agrega info extra
        fila_cp = fila.copy()
        fila_cp["pais_scrapeado"] = sheet_name
        fila_cp["items_filtrados"] = top3
        fila_cp["row_index"] = row_index       
        publicaciones.append(fila_cp)

    # ---------- DEBUG opcional ----------
    if publicaciones:
        import pandas as pd

        # Aplanamos las listas para ver una fila ↔ un ítem (más cómodo de inspeccionar)
        debug_rows = []
        for pub in publicaciones:
            for it in pub["items_filtrados"]:
                row = {
                    "kw": pub["Producto"],
                    "asin": it.get("asin"),
                    "titulo": it.get("titulo", "")[:50] + "…",
                    **{f"img{i+1}": it.get(f"imagen{i+1}") for i in range(6)},
                }
                debug_rows.append(row)

        df = pd.DataFrame(debug_rows)
        with pd.option_context(
            "display.max_columns", None,
            "display.max_colwidth", 80,
            "display.width", 0,            # ajuste automático de ancho
        ):
            print("\n=== PREVIEW ÍTEMS ARMADOS (con 6 fotos) ===")
            print(df.head(10))  # muestra las primeras 10 filas

    return publicaciones 

# ─────────────── helpers ───────────────
def preparar_tabla_b(publicaciones: list[dict], header_row: list[str]) -> list[dict]:
    filas_out = []

    for pub in publicaciones:
        row_index = pub.get("row_index")
        pais_scrapeado = pub.get("pais_scrapeado")
        precio_aliexpress = float_safe(pub.get("precio_aliexpress"))

        for item in pub["items_filtrados"]:
            fila = {col: pub.get(col, "") for col in header_row}

            precio_amazon = float_safe(item.get("precio"))
            reviews = int(item.get("reviews") or 0)
            producto = item.get("titulo", "") or pub.get("Producto", "")

            # Control de marca
            if es_producto_de_marca(producto):
                precio_venta_sugerido = precio_amazon  # mostrar precio real
                margen_estimado = ""                   # no mostrar ganancia inventada
            else:
                margen_ratio = calcular_margen_ratio(precio_amazon, pais_scrapeado, reviews)
                precio_venta_sugerido = round(precio_amazon * (1 + margen_ratio), 2)
                margen_estimado = round(precio_venta_sugerido - precio_aliexpress, 2)

            fila.update({
                "precio_amazon": precio_amazon,
                "precio_venta_sugerido": precio_venta_sugerido,
                "margen_estimado": margen_estimado,
                "imagen": url_safe(item.get("imagen1", item.get("imagen"))),
                "imagen2": url_safe(item.get("imagen2")),
                "imagen3": url_safe(item.get("imagen3")),
                "imagen4": url_safe(item.get("imagen4")),
                "imagen5": url_safe(item.get("imagen5")),
                "imagen6": url_safe(item.get("imagen6")),
                "row_index": row_index,
                "pais_scrapeado": pais_scrapeado
            })

            filas_out.append(fila)

    # Preview opcional
    if filas_out:
        import pandas as pd
        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_colwidth", None)
        pd.set_option("display.width", 0)

        print("\n=== PREVIEW COMPLETO TABLA B ===")
        print(pd.DataFrame(filas_out))

    return filas_out


# ──────────────────────────────────────────────────────────────
# (c) Reduce las publicaciones a la forma que entiende el frontend
# ──────────────────────────────────────────────────────────────
def preparar_respuesta_ui(publicaciones):
    """
    Reduce las 'publicaciones' a los 3 mejores items por producto, 
    basados en reviews > rating > precio válido.
    """
    datos_ui = []

    for pub in publicaciones:
        items = pub.get("items", [])

        # Filtrar con precio > 0
        items_filtrados = [it for it in items if it.get("precio", 0) > 0]

        # Ordenar por reviews (desc), luego rating (desc), luego precio (asc)
        def criterio(it):
            try:
                revs = int(it.get("reviews", 0))
                rating_txt = it.get("rating", "0 su 5 stelle")
                rating = float(rating_txt.replace(",", ".").split(" ")[0])
            except:
                revs, rating = 0, 0
            return (-revs, -rating)

        mejores = sorted(items_filtrados, key=criterio)[:3]

        if mejores:
            datos_ui.append({
                "producto": pub["producto"],
                "pais": pub["pais"],
                "items": [
                    {
                        "titulo": it["titulo"],
                        "imagen": it["imagen"],
                        "precio": it["precio"],
                        "url": it["url"],
                        "rating": it.get("rating"),
                        "reviews": it.get("reviews"),
                        "prime": it.get("prime"),
                        "asin": it.get("asin"),
                        "entrega": it.get("entrega")
                    }
                    for it in mejores
                ]
            })
        

    return datos_ui














def _as_url(v):
    """Extrae la URL si viene como dict, si no deja el string tal cual."""
    if isinstance(v, dict):
        return v.get("imageUrl", "")
    return v or ""

def _base(url: str) -> str:
    """Quita el sufijo de tamaño Amazon (_AC_UL320_, _SX522_, …)."""
    return SIZE_TAG.sub(r'.\1', url) if url else url








def obtener_galeria_en_batches(asins: List[str], apify_token: str, dominio: str = "com", batch_size: int = 5) -> Dict[str, List[str]]:
    from time import sleep

    resultados = {}

    for i in range(0, len(asins), batch_size):
        batch = asins[i:i + batch_size]
        print(f"🎞️  Procesando batch de galería {i // batch_size + 1}...", flush=True)

        for asin in batch:
            try:
                galeria = obtener_galeria(asin, apify_token, dominio)
                resultados[asin] = galeria
            except Exception as e:
                print(f"❌ Error obteniendo galería para ASIN {asin}: {e}", flush=True)
                resultados[asin] = [""] * 6

        sleep(1)  # pausa corta entre batches

    return resultados







def obtener_galeria(asin: str, apify_token: str, dominio: str = "com") -> List[str]:
    if not asin:
        return [""] * 6
    print(f"[DEBUG] dentro 8888888888888888888   obtener_galeria()", flush=True)
    actor_id = "7KgyOHHEiPEcilZXM"
    endpoint = (
        f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
        f"?token={apify_token}&format=json"
    )

    url_producto = f"https://www.amazon.{dominio}/dp/{asin}"
    payload = {"urls": [url_producto]}
    
    try:
        items = requests.post(endpoint, json=payload, timeout=90).json() or []
        item  = items[0] if items else {}
        mini  = _as_url(item.get("mainImage"))
        gal   = [_as_url(u) for u in item.get("imageUrlList", [])]
    except Exception as e:
        print("⚠️  Error obteniendo galería:", e, flush=True)
        mini, gal = "", []

    # Normaliza y deduplica por “base” (sin sufijo de tamaño)
    vistas, fotos = set(), []
    for url in [mini] + gal:
        if not url:
            continue
        key = _base(url)
        if key not in vistas:
            vistas.add(key)
            fotos.append(url)

    fotos = (fotos + [""] * 6)[:6]          # rellena a 6
    return fotos



def guardar_respuesta_json(publicaciones: List[Dict], nombre_archivo: str = None) -> str:
    """
    Guarda la lista 'publicaciones' en un archivo JSON dentro de 'src/static/downloads/'.
    Retorna el nombre del archivo guardado (no la ruta completa).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not nombre_archivo:
        nombre_archivo = f"resultados_scraping_{timestamp}.json"
    else:
        # Asegura nombre sin caracteres inválidos
        nombre_archivo = f"{nombre_archivo}_{timestamp}.json".replace(" ", "_")

    # Crear carpeta si no existe
    os.makedirs(BASE_STATIC_DOWNLOADS, exist_ok=True)

    ruta_guardado = os.path.join(BASE_STATIC_DOWNLOADS, nombre_archivo)

    try:
        with open(ruta_guardado, "w", encoding="utf-8") as f:
            json.dump(publicaciones, f, indent=2, ensure_ascii=False)
        print(f">>> Publicaciones guardadas en: {os.path.abspath(ruta_guardado)}", flush=True)
    except Exception as e:
        print(f"❌ Error al guardar el JSON: {e}", flush=True)
        raise  # Opcional: lanzar el error para que el caller lo maneje

    return nombre_archivo






def es_producto_de_marca(producto: str) -> bool:
    if not producto:
        return False
    producto_lower = producto.lower()
    return any(marca in producto_lower for marca in MARCAS_RESTRINGIDAS)


def float_safe(v) -> float:
    try:
        return float(str(v).replace(",", "."))
    except:
        return 0.0

def url_safe(v) -> str:
    return v.get("imageUrl", "") if isinstance(v, dict) else (v or "")

def calcular_margen_ratio(precio: float, pais: str, reviews: int = 0) -> float:
    if precio <= 0:
        return 0.0

    # Margen base según precio
    if precio < 10:
        base = 1.2  # 120%
    elif precio < 25:
        base = 0.7  # 70%
    else:
        base = 0.5  # 50%

    # Ajuste por país
    pais = (pais or "").lower()
    if pais in ["alemania", "italia", "estados_unidos"]:
        base += 0.1
    elif pais in ["argentina", "peru", "colombia"]:
        base -= 0.1

    # Ajuste por popularidad
    if reviews > 5000:
        base += 0.15
    elif reviews > 1000:
        base += 0.05

    # Variabilidad controlada
    ruido = random.uniform(-0.05, 0.05)
    return round(base + ruido, 2)