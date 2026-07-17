import os
import requests
from flask import Blueprint, request, jsonify
import json,pathlib, time
import re
from pathlib import Path
import math
from collections import defaultdict
from json import JSONDecoder
from controllers.conexionesSheet.datosSheet import login, autenticar_y_abrir_sheet,leerSheet,actualizar_estado_en_sheet
from controllers.filtro_publicacion import filtro_publicaciones,guardar_respuesta_json,armar_publicaciones_validas_match_scrping_sheet,preparar_respuesta_ui,preparar_tabla_b
from controllers.publicaciones import completar_publicaciones
from typing import List, Dict
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


# 📌 Token y Task ID de Apify
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

TASK_ID = "ruly_economy/dpia-amazon"

ACTOR_ID = "axesso_data~amazon-search-scraper"

SHEET_ID_DETECTOR_TENDENCIA = '1munTyxoLc5px45cz4cO_lLRrqyFsOwjTUh8xDPOiHOg'

BASE_STATIC_DOWNLOADS = os.path.join( "static", "downloads")

SHEET_ID_DETECTOR_TENDENCIA = os.environ.get('SHEET_ID_DETECTOR_TENDENCIA')
# Configuración de cada marketplace
MARKETS = {
    "amazon": {
        "actor": "axesso_data~amazon-search-scraper",
        "domains": {
            "argentina": "com.ar", "canada": "ca", "francia": "fr", "italia": "it",
            "estados_unidos": "com", "alemania": "de", "espana": "es", "polonia": "pl"
        }
    },
    "ebay": {
        "actor": "axesso_data~ebay-search-scraper",
        "domains": {
            "argentina": "com.ar", "canada": "ca", "francia": "fr", "italia": "it",
            "estados_unidos": "com", "alemania": "de", "espana": "es", "polonia": "pl"
        }
    },
    "aliexpress": {
        "actor": "axesso_data~aliexpress-search-scraper",
        "domains": {
            # AliExpress no cambia mucho de dominio, pero podrías mapear países a idiomas
            "argentina": "com", "canada": "com", "francia": "fr", "italia": "it",
            "estados_unidos": "com", "alemania": "de", "espana": "es", "polonia": "pl"
        }
    },
    "mercadolibre": {
        "actor": "apify/mercadolibre-scraper",
        "domains": {
            "argentina": "com.ar", "mexico": "com.mx", "colombia": "com.co",
            "chile": "cl", "brasil": "com.br", "venezuela": "com.ve"
            # añade los que necesites
        }
    }
}

# 📍 Blueprint
scrape_amazon_dpia = Blueprint('scrape_amazon_dpia', __name__)


# 1. Calcula la ruta al directorio raíz de tu proyecto (dos niveles arriba de este archivo)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))




# —————— Orquestador en tu endpoint ——————

def load_many(json_path):
    # 1) Leemos todo el fichero
    with open(json_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # 2) Convertimos cualquier ‘}{’ o ‘},\n{’ en '},{' para asegurarnos de que quede "obj1},{obj2"
    text = re.sub(r'}\s*{', '},{', text)

    # 3) Si no empieza con '[', lo envolvemos en corchetes
    if not text.startswith('['):
        text = f'[{text}]'

    # 4) Eliminamos comas finales justo antes del ']'
    text = re.sub(r',\s*]', ']', text)

    # 5) Parseamos JSON
    datos = json.loads(text)

    # 6) Tu salida de depuración / resumen
    for sección in datos:
        #print(f"{sección['asin']} – {sección['productDescription'][:60]}...")
        print(f"{sección['producto']} → {len(sección['items'])} items")

    return datos






@scrape_amazon_dpia.route('/scrape_amazon_listar_trabajos/', methods=['POST'])
def scrape_amazon_listar_trabajos():
    try:
        data = request.get_json()
        lugar = data.get('lugar', 'Argentina')

        folder_path = os.path.join(BASE_DIR, "src", "static", "downloads")
        archivos = [
            f for f in os.listdir(folder_path)
            if f.startswith(f"{lugar}") and f.endswith(".json")
        ]

        return jsonify(success=True, archivos=archivos)

    except Exception as e:
        return jsonify(success=False, error=str(e))

    
@scrape_amazon_dpia.route('/scrape_amazon_eliminar_archivo/', methods=['POST']) 
def scrape_amazon_eliminar_archivo():
    try:
        archivo = request.form.get("archivo")
        if not archivo:
            return jsonify(success=False, error="Nombre de archivo no especificado.")
        
        base_path = os.path.join(BASE_DIR, "src", "static", "downloads")
        archivo_path = os.path.join(base_path, archivo)
        
        if not os.path.exists(archivo_path):
            return jsonify(success=False, error="El archivo no existe.")

        # Cargar relaciones
        relaciones_path = os.path.join(base_path, "relaciones_archivos.json")
        with open(relaciones_path, "r", encoding="utf-8") as f:
            relaciones = json.load(f)

        nuevas_relaciones = []
        for relacion in relaciones.get("spoleto", []):
            if relacion["principal"] == archivo:
                # Eliminar archivos relacionados
                for dependiente in relacion.get("relacionados", []):
                    dep_path = os.path.join(base_path, dependiente)
                    if os.path.exists(dep_path):
                        os.remove(dep_path)
                        print(f"Eliminado archivo dependiente: {dependiente}")
            elif archivo not in relacion.get("relacionados", []):
                nuevas_relaciones.append(relacion)
            # Si el archivo está en 'relacionados', también se elimina la relación completa
            # (esto es lo que hacías ya)
        
        # Eliminar archivo principal
        os.remove(archivo_path)

        # Guardar nuevas relaciones
        relaciones["spoleto"] = nuevas_relaciones
        with open(relaciones_path, "w", encoding="utf-8") as f:
            json.dump(relaciones, f, indent=2, ensure_ascii=False)

        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, error=str(e))




    
    
 # 📍 Endpoint que se invoca desde el botón Scrapeado Imágenes arma la tabla 2   






@scrape_amazon_dpia.route('/scrape_amazon_dpia_scraping_imagenes/', methods=['POST'])
def scrape_amazon_dpia_scraping_imagenes():
      try:
        # Recibo sheet_name (p.ej. "Polonia") del front
        sheet_name = request.get_json().get("sheet_name")
        sheetId = '1munTyxoLc5px45cz4cO_lLRrqyFsOwjTUh8xDPOiHOg'
        sheet = autenticar_y_abrir_sheet(SHEET_ID_DETECTOR_TENDENCIA, sheet_name)
        nombre_archivo = request.get_json().get("nombre_archivo")
        archivo_base = request.get_json().get("archivo_base")
        resultados = []
        if not sheet:
            return jsonify(success=False, error="No pude abrir la hoja")

        # 1) Traigo todas las filas
        # 1) Obtener encabezado
        header = sheet.row_values(1)

        # 2) Leer todas las filas con índice real del Sheet
        filas = []
        for idx, row in enumerate(sheet.get_all_values()[1:], start=2):  # empieza en la fila 2
            fila_dict = dict(zip(header, row))
            fila_dict["row_index"] = idx
            filas.append(fila_dict)

        
        # 2) Filtro sólo las que necesito
        #    Ajusta las condiciones al gusto:
        filas_validas = [
            f for f in filas 
            if f.get("Producto")
            and f.get("estado", "").upper() == "ACTIVO"
            and str(f.get("validado", "")).upper() == "FALSE"
        ]

        if not filas_validas:
            return jsonify(success=True, datos=[])
        
        
        
       
     
       # 2. Construye la ruta al JSON dentro de test/
        json_path = os.path.join(BASE_DIR, "src", "static", "downloads", nombre_archivo)

        print(f"[DEBUG] Ruta al archivo JSON principal: {json_path}", flush=True)
        print(f"[DEBUG] ¿Existe archivo principal?: {os.path.exists(json_path)}", flush=True)

        resultados_globales = load_many(json_path)
    
        print(f"[DEBUG] Ruta al archivo JSON principa44444444444444444l: {json_path}", flush=True)
        print(f"[DEBUG] Total filas encontradas: {len(filas)}", flush=True)
        print(f"[DEBUG] Filas validadas encontradas: {len(filas_validas)}", flush=True)
        
        # (b) arma filas + top-3
        # aqui se llama al scraping de imágenes
        publicaciones = armar_publicaciones_validas_match_scrping_sheet(
                                                                            filas_validas,
                                                                            resultados_globales,
                                                                            sheet_name,
                                                                            APIFY_TOKEN,         
                                                                       )
        # esto sirve para armar el segundo archivo de test
        ruta_archivo_con_imagenes = guardar_respuesta_json(publicaciones, 'publicaciones_' + sheet_name)
        
        guardar_relacion_archivos_con_principal(sheet_name, ruta_archivo_con_imagenes, archivo_base)
      
        # (c) reduce a la estructura que entiende el front
       # '/workspaces/seleniumicro/src/static/downloads/publicaciones_20250714_080406.json'
        json_path_2 = os.path.join(BASE_DIR, "src", "static", "downloads", archivo_base)
        print(f"[DEBUG] Ruta al archivo JSON principal: {json_path_2}", flush=True)
        print(f"[DEBUG] ¿Existe archivo principal?: {os.path.exists(json_path_2)}", flush=True)

        with open(json_path_2, "r", encoding="utf-8") as f:
            publicaciones_tablaa = json.load(f)
        tabla_a = preparar_respuesta_ui(publicaciones_tablaa)   # (la que ya tenías)
        
        
        json_path_3 = os.path.join(BASE_DIR, "src", "static", "downloads", ruta_archivo_con_imagenes)
        print(f"[DEBUG] Ruta al archivo JSON principal: {json_path_3}", flush=True)
        print(f"[DEBUG] ¿Existe archivo principal?: {os.path.exists(json_path_3)}", flush=True)

        with open(json_path_3, "r", encoding="utf-8") as f:
            publicaciones_tablab = json.load(f)
       
        # header real de la hoja
        sheet_header = sheet.row_values(1)
        tabla_b = preparar_tabla_b(publicaciones_tablab, sheet_header)
       
      

        
        return jsonify(success=True, tablaA=tabla_a, tablaB=tabla_b,archivo_relacionado=ruta_archivo_con_imagenes)

      except Exception as e:
          return jsonify(success=False, error=str(e))

    
    
    
    # 📍 Endpoint que se invoca desde el botón Scrapeado
@scrape_amazon_dpia.route('/scrape_amazon_scrapeado/', methods=['POST'])
def scrape_amazon_scrapeado():
    try:
     #   print("[DEBUG] 🔄 Iniciando función scrape_amazon_scrapeado", flush=True)

        data = request.get_json()
      #  print("[DEBUG] ✅ JSON recibido:", data)
        sheet_name = data.get("sheet_name")
        nombre_archivo = data.get('nombre_archivo')
        sheetId = '1munTyxoLc5px45cz4cO_lLRrqyFsOwjTUh8xDPOiHOg'
        
        print("[DEBUG] cwd:jjjjjjjjjjjjjjjjjjjjjjjjjjjjj", flush=True)  
        print("[DEBUG] cwd:", os.getcwd(), flush=True)
        print(f"[DEBUG] sheet_name recibido: {sheet_name}", flush=True)
        print(f"[DEBUG] nombre_archivo recibido: {nombre_archivo}", flush=True)

        sheet = autenticar_y_abrir_sheet(SHEET_ID_DETECTOR_TENDENCIA, sheet_name)
        if not sheet:         

            return jsonify(success=False, error="No pude abrir la hoja")

        # Obtener encabezado y todas las filas
        header = sheet.row_values(1)
        filas = []
        for idx, row in enumerate(sheet.get_all_values()[1:], start=2):
            fila_dict = dict(zip(header, row))
            fila_dict["row_index"] = idx
            filas.append(fila_dict)

        # Filtrar solo filas activas y no validadas
       
        print(f"[DEBUG] scrape_amazon_scrapeado Total filas encontradas: {len(filas)}", flush=True)
      
        obtener_archivos = obtener_set_por_principal(sheet_name, nombre_archivo)
        if not obtener_archivos:
            return jsonify(success=False, error="No hay archivos disponibles para este sheet.")
        
        print(f"[DEBUG] Archivos disponibles para {sheet_name}: {obtener_archivos}", flush=True)

        archivo_relacionado = obtener_archivos.get("relacionados", [None])[0]
        if not archivo_relacionado:
            return jsonify(success=False, error="No hay archivo relacionado.")

        # Ruta al archivo principal
        json_path = os.path.join(BASE_DIR, "src","static", "downloads", nombre_archivo)
        print(f"[DEBUG] Ruta al archivo JSON principal: {json_path}", flush=True)
        print(f"[DEBUG] ¿Existe archivo principal?: {os.path.exists(json_path)}", flush=True)

        resultados_globales = load_many(json_path)

        # Ruta al archivo relacionado
        json_path_2 = os.path.join(BASE_DIR, "src", "static", "downloads", archivo_relacionado)
        print(f"[DEBUG] Ruta al archivo relacionado: {json_path_2}", flush=True)
        print(f"[DEBUG] ¿Existe archivo relacionado?: {os.path.exists(json_path_2)}", flush=True)

        with open(json_path_2, "r", encoding="utf-8") as f:
            publicaciones = json.load(f)

        tabla_a = preparar_respuesta_ui(resultados_globales)
        sheet_header = sheet.row_values(1)
        tabla_b = preparar_tabla_b(publicaciones, sheet_header)


        print(f"[DEBUG]  tabla_a (primer item): {tabla_a[0] if tabla_a else 'VACÍO'}", flush=True)
        print(f"[DEBUG]  tabla_b (primer item): {tabla_b[0] if tabla_b else 'VACÍO'}", flush=True)
        print(f"[DEBUG] Total items en tabla_a: {len(tabla_a)}", flush=True)
        print(f"[DEBUG] Total items en tabla_b: {len(tabla_b)}", flush=True)


        return jsonify(success=True, tablaA=tabla_a, tablaB=tabla_b, archivo_relacionado=archivo_relacionado)

    except Exception as e:
        return jsonify(success=False, error=str(e))














# 📍 Endpoint que se invoca desde el botón
@scrape_amazon_dpia.route('/scrape_amazon/', methods=['POST'])
def scrape_amazon():
      try:
        # Recibo sheet_name (p.ej. "Polonia") del front
        sheet_name = request.get_json().get("sheet_name")
        sheetId = '1munTyxoLc5px45cz4cO_lLRrqyFsOwjTUh8xDPOiHOg'
        print("[DEBUG] Llamando a autenticar_y_abrir_sheet()", flush=True)
        sheet = autenticar_y_abrir_sheet(SHEET_ID_DETECTOR_TENDENCIA, sheet_name)
        resultados = []
        if not sheet:
            return jsonify(success=False, error="No pude abrir la hoja")

        # 1) Traigo todas las filas
        # 1) Obtener encabezado
        header = sheet.row_values(1)

        # 2) Leer todas las filas con índice real del Sheet
        filas = []
        for idx, row in enumerate(sheet.get_all_values()[1:], start=2):  # empieza en la fila 2
            fila_dict = dict(zip(header, row))
            fila_dict["row_index"] = idx
            filas.append(fila_dict)


        # 2) Filtro sólo las que necesito
        #    Ajusta las condiciones al gusto:
        filas_validas = [
            f for f in filas 
            if f.get("Producto")
            and f.get("estado", "").upper() == "ACTIVO"
            and str(f.get("validado", "")).upper() == "FALSE"
        ]

        if not filas_validas:
            return jsonify(success=True, datos=[])

        # 3) Llamo al scraper **una sola vez** con la lista entera
        # (a) SCRAPING: aquí usarías lanzar_scraping_amazon(...)
        # # # # # # # # resultados_globales = lanzar_scraping_amazon(filas_validas, sheet_name) # # # # # # # # # # # 
      
        resultados_globales = lanzar_scraping_amazon_en_batches(filas_validas, sheet_name) # por batches de 5

      
      
      # esto guarda el primer archivo de test
     
      
       # NAME_ARCHIVO_1 = "resultados_scraping_20250722_120527.json"
       # NAME_ARCHIVO_2 = "publicaciones_20250722_131346.json"
       # 2. Construye la ruta al JSON dentro de test/
       # json_path = os.path.join(BASE_DIR, "src", "static", "downloads", NAME_ARCHIVO_1)


       # resultados_globales = load_many(json_path)
      # 1. Cargar resultados previamente guardados
      
      #esto abre el archivo de test
       # resultados_globales = cargar_resultados_scraping_desde_archivo("resultados_scraping_20250722_104834.json")

        
        # (b) arma filas + top-3
       # publicaciones = armar_publicaciones_validas_match_scrping_sheet(
       #                                                                     filas_validas,
        #                                                                    resultados_globales,
         #                                                                   sheet_name,
         #                                                                   APIFY_TOKEN,         
        #                                                               )
        # esto sirve para armar el segundo archivo de test
       # ruta_archivo = guardar_publicaciones_json(publicaciones)
     
        tabla_a = preparar_respuesta_ui(resultados_globales)   # (la que ya tenías)
        nombre_archivo = guardar_respuesta_json(tabla_a,sheet_name)
        
        # header real de la hoja
        sheet_header = sheet.row_values(1)
       # tabla_b = preparar_tabla_b(resultados_globales, sheet_header)
        tabla_b = [] 
      

        
        return jsonify(success=True, tablaA=tabla_a, tablaB=tabla_b, archivo_base=nombre_archivo)

      except Exception as e:
          return jsonify(success=False, error=str(e))















def lanzar_scraping_amazon_en_batches(registros: list, pais_defecto: str, batch_size: int = 5) -> list:
    from time import sleep
    resultados_finales = []

    for i in range(0, len(registros), batch_size):
        batch = registros[i:i + batch_size]
        print(f"⏳ Ejecutando batch {i // batch_size + 1} de {math.ceil(len(registros) / batch_size)}...")

        try:
            resultados = lanzar_scraping_amazon(batch, pais_defecto)
            resultados_finales.extend(resultados)

        except Exception as e:
            print(f"❌ Error en el batch {i // batch_size + 1}: {e}")
            for fila in batch:
                resultados_finales.append({
                    "producto": fila["Producto"],
                    "pais": fila["País"],
                    "row_index": fila.get("row_index"),
                    "error": f"Error en batch: {str(e)}"
                })

        sleep(1)  # opcional: pausa breve entre batches para no sobrecargar Apify

    return resultados_finales















def lanzar_scraping_amazon(registros: list, pais_defecto: str = "com") -> list:
    dominio_por_pais = {
        "argentina": "com", "canada": "ca", "francia": "fr", "italia": "it",
        "estados_unidos": "com", "alemania": "de", "espana": "es", "polonia": "pl"
    }
    ACTOR_ID = "axesso_data~amazon-search-scraper"
    base_url = (
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        f"?token={APIFY_TOKEN}"
    )

    # 1) Payload
    payload = {
        "input": [
            {
                "keyword":    fila["Producto"],
                "domainCode": dominio_por_pais.get(fila.get("País", "").lower(), pais_defecto),
                "sortBy":     "recent",
                "maxPages":   1,
                "category":   "aps",
            }
            for fila in registros
        ]
    }

    # 2) Request
    resp = requests.post(base_url, json=payload, timeout=90)
    resp.raise_for_status()
    datos = resp.json()
    if not isinstance(datos, list) or not datos:
        raise ValueError("Respuesta vacía o inválida.")

    # 3) Agrupar por keyword
    por_kw = defaultdict(list)
    for it in datos:
        kw = it.get("keyword")
        if kw:
            por_kw[kw].append(it)

    # 4) Reconstruir resultados (solo si hay items válidos)
    resultados = []
    for fila in registros:
        prod = fila["Producto"]
        pais = fila.get("País", "")
        row_index = fila.get("row_index")

        raw_items = por_kw.get(prod, [])
        base_dom = dominio_por_pais.get(pais.lower(), pais_defecto)

        items = []
        vistos_asin = set()

        for d in raw_items:
            desc = (d.get("productDescription") or "").strip()
            price = d.get("price")

            # Debe tener descripción y precio válido
            if not desc or price in (None, "", 0):
                continue

            asin = d.get("asin")
            if asin and asin in vistos_asin:
                continue  # dedupe
            if asin:
                vistos_asin.add(asin)

            url_dp = d.get("dpUrl")
            url_final = f"https://www.amazon.{base_dom}{url_dp}" if url_dp else None

            items.append({
                "titulo":          desc,
                "asin":            asin,
                "precio":          price,
                "precio_original": d.get("retailPrice"),
                "rating":          d.get("productRating"),
                "reviews":         d.get("countReview"),
                "prime":           d.get("prime"),
                "entrega":         d.get("deliveryMessage"),
                "imagen":          d.get("imgUrl"),
                "url":             url_final,
                "detalles":        d.get("productDetails", []),
            })

        # ⬇️ Clave: si NO hay items válidos, NO agregamos nada
        if not items:
            continue

        resultados.append({
            "producto":  prod,
            "pais":      pais,
            "row_index": row_index,
            "items":     items,
        })

    return resultados



# ── 1)  Configurá el driver ─────────────────────────
def get_chrome():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")   # sin UI
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

driver = get_chrome()

# ── 2)  Función que abre el DP y llama al helper ─────
def extraer_imagenes_por_asin(asin: str, dominio: str, driver) -> list:
    url = f"https://www.amazon.{dominio}/dp/{asin}"
    driver.get(url)
    return extraer_imagenes(driver)

# ── 3)  Helper para tomar hasta 6 URLs hi-res ────────
def extraer_imagenes(driver):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "imgTagWrapperId"))
    )

    thumbs = driver.find_elements(By.CSS_SELECTOR, "#altImages li img")
    urls = set()

    for thumb in thumbs:
        try:
            thumb.click()
            time.sleep(0.5)  # deja que cambie la imagen grande
            tag  = driver.find_element(By.ID, "landingImage")
            data = tag.get_attribute("data-a-dynamic-image")
            hi_res = list(json.loads(data).keys())[0]
            urls.add(hi_res)
        except Exception:
            pass

    return list(urls)[:6]   # máx 6










def lanzar_scraping_aliexpress(registros: list, pais_defecto: str) -> list:
    import json, pathlib, requests
    # actor y dominio para AliExpress
    ACTOR_ID = "axesso_data~aliexpress-search-scraper"
    dominio_por_pais = {
        "argentina":"com","canada":"com","francia":"fr","italia":"it",
        "estados_unidos":"com","alemania":"de","espana":"es","polonia":"pl"
    }
    base_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    # payload idéntico al de Amazon
    payload = {"input":[
        {
            "keyword": fila["Producto"],
            "domainCode": dominio_por_pais.get(fila.get("País","").lower(),"com"),
            "sortBy": "recent",
            "maxPages": 1,
            "category": "aps"
        }
        for fila in registros
    ]}

    resp = requests.post(base_url, json=payload, timeout=90)
    resp.raise_for_status()
    datos = resp.json()

    # agrupo por keyword
    agrupado = defaultdict(list)
    for item in datos:
        kw = item.get("keyword")
        agrupado[kw].append(item)

    # construyo resultados
    resultados = []
    for fila in registros:
        prod = fila["Producto"]
        raw = agrupado.get(prod, [])
        items = []
        for d in raw:
            if d.get("productDescription"):
                items.append({
                    "titulo": d["productDescription"],
                    "precio": d.get("price","N/A"),
                    "imagen": d.get("imgUrl",""),
                    "url":     f"https://www.aliexpress.{dominio_por_pais.get(fila.get('País','').lower(),'com')}{d.get('dpUrl','')}"
                })
        resultados.append({
            "producto": prod,
            "pais":     fila["País"],
           
            "items":    items or [],
            "error":    None if items else "Sin productos relevantes"
        })
    return resultados

def lanzar_scraping_ebay(registros: list, pais_defecto: str) -> list:
    ACTOR_ID = "dtrungtin/ebay-items-scraper"  # tu Actor ID exacto
    dominio_por_pais = {
        "argentina": "com.ar","canada": "ca","francia": "fr",
        "italia": "it","estados_unidos": "com","alemania": "de",
        "espana": "es","polonia": "pl"
    }

    # 1) Construyo la lista de startUrls, una por fila
    start_urls = [
        {
          "url": (
             f"https://www.ebay.{ dominio_por_pais.get(fila['País'].lower(), 'com') }"
             f"/sch/i.html?_nkw={fila['Producto'].replace(' ', '+')}"
          )
        }
        for fila in registros
    ]
    payload = {
        "proxyConfig": {"useApifyProxy": True},
        "maxItems":    5,       # ajusta cuántos items por búsqueda
        "startUrls":   start_urls
    }

    # 2) Lanzar la petición
    resp = requests.post(
      f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}",
      json=payload,
      timeout=90
    )
    resp.raise_for_status()
    datos = resp.json()

    # 3) Agrupo los items por la URL original
    agrupado = defaultdict(list)
    for d in datos:
        req = d.get("request", {})  # este actor incluye request.url
        url = req.get("url")
        if url:
            agrupado[url].append(d)

    # 4) Construyo el output paralelo a tus registros
    resultados = []
    for fila in registros:
        code       = dominio_por_pais.get(fila['País'].lower(), 'com')
        search_url = (
          f"https://www.ebay.{code}/sch/i.html?_nkw={fila['Producto'].replace(' ', '+')}"
        )
        raw_items = agrupado.get(search_url, [])
        items = []
        for d in raw_items:
            # ajusta estos campos si tu actor los devuelve con otro nombre
            titulo = d.get("title") or d.get("productDescription")
            precio = d.get("price")
            img    = d.get("image") or d.get("imgUrl")
            link   = d.get("url") or d.get("itemUrl")
            if titulo and precio:
                items.append({
                    "titulo": titulo,
                    "precio": precio,
                    "imagen": img,
                    "url":     link
                })

        resultados.append({
            "producto": fila["Producto"],
            "pais":     fila["País"],
            "items":    items,
            "error":    None if items else "Sin resultados en eBay"
        })

    return resultados






def lanzar_scraping_ml(registros: list, pais_defecto: str) -> list:
    # equivalente para MercadoLibre
    ACTOR_ID = "apify/mercadolibre-scraper"
    dominio_por_pais = {
        "argentina":"com.ar","mexico":"com.mx","colombia":"com.co",
        "chile":"cl","brasil":"com.br","venezuela":"com.ve"
    }
    base_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
       # payload idéntico al de Amazon
    payload = {"input":[
        {
            "keyword": fila["Producto"],
            "domainCode": dominio_por_pais.get(fila.get("País","").lower(),"com"),
            "sortBy": "recent",
            "maxPages": 1,
            "category": "aps"
        }
        for fila in registros
    ]}

    resp = requests.post(base_url, json=payload, timeout=90)
    resp.raise_for_status()
    datos = resp.json()

    # agrupo por keyword
    agrupado = defaultdict(list)
    for item in datos:
        kw = item.get("keyword")
        agrupado[kw].append(item)

    # construyo resultados
    resultados = []
    for fila in registros:
        prod = fila["Producto"]
        raw = agrupado.get(prod, [])
        items = []
        for d in raw:
            if d.get("productDescription"):
                items.append({
                    "titulo": d["productDescription"],
                    "precio": d.get("price","N/A"),
                    "imagen": d.get("imgUrl",""),
                    "url":     f"https://www.aliexpress.{dominio_por_pais.get(fila.get('País','').lower(),'com')}{d.get('dpUrl','')}"
                })
        resultados.append({
            "producto": prod,
            "pais":     fila["País"],
            "items":    items or [],
            "error":    None if items else "Sin productos relevantes"
        })
    return resultados











def cargar_resultados_scraping_desde_archivo(nombre_archivo: str) -> List[Dict]:
    """
    Carga y devuelve el contenido JSON del archivo en static/downloads/<nombre_archivo>.
    """
    ruta = os.path.join("src", "static/downloads", nombre_archivo)

    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)

    if not isinstance(datos, list):
        raise ValueError(f"El archivo no contiene una lista válida de resultados: {ruta}")



















def guardar_relacion_archivos_con_principal(sheet_name, archivo_relacionado, archivo_base: str = None) -> str:
    relacion_path = os.path.join(BASE_STATIC_DOWNLOADS, "relaciones_archivos.json")

    # Cargar si ya existe
    if os.path.exists(relacion_path):
        with open(relacion_path, "r", encoding="utf-8") as f:
            try:
                relaciones = json.load(f)
            except:
                relaciones = {}
    else:
        relaciones = {}

    # Generar nombre del archivo relacionado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not archivo_relacionado:      
        archivo_relacionado = f"publicaciones_{sheet_name}_{timestamp}.json"

    # Estructura del set nuevo
    nuevo_set = {
        "principal": archivo_base,
        "relacionados": [archivo_relacionado]
    }

    # Inicializar si no hay entrada
    if sheet_name not in relaciones:
        relaciones[sheet_name] = []

    # Evitar duplicados exactos
    ya_existe = any(
        r["principal"] == archivo_base and archivo_relacionado in r.get("relacionados", [])
        for r in relaciones[sheet_name]
    )

    if not ya_existe:
        relaciones[sheet_name].append(nuevo_set)

    # Guardar actualizado
    with open(relacion_path, "w", encoding="utf-8") as f:
        json.dump(relaciones, f, indent=2, ensure_ascii=False)

    return archivo_relacionado  # Devuelve el nombre generado si querés usarlo luego




def obtener_set_por_principal(sheet_name, archivo_principal_buscado):
    sets = obtener_archivos_por_sheet(sheet_name)  # devuelve la lista de sets
    for s in sets:
        if s.get("principal") == archivo_principal_buscado:
            return s
    return None



def obtener_archivos_por_sheet(sheet_name):
    relacion_path = os.path.join(BASE_STATIC_DOWNLOADS, "relaciones_archivos.json")
    
    if not os.path.exists(relacion_path):
        return None

    with open(relacion_path, "r", encoding="utf-8") as f:
        relaciones = json.load(f)
    
    return relaciones.get(sheet_name)
