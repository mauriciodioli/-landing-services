from flask import Blueprint, render_template, request,current_app, redirect, url_for, flash,jsonify
from datetime import datetime
import enum
from models.sheetModels.GoogleSheetManager import GoogleSheetManager
from models.sheetModels.sheet_handler import SheetHandler
import copy
import socket
import requests
import time
import json

from extensions import db

import random
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
#import routes.api_externa_conexion.cuenta as cuenta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from controllers.conexionesSheet.datosSheet import login, autenticar_y_abrir_sheet
from controllers.publicaciones import completar_publicaciones
from models.create_tablas import crea_tablas_DB
import pprint
import os #obtener el directorio de trabajo actual
import json
import sys



conexion_externa = Blueprint('conexion_externa',__name__)

autenticado_sheet = False

# 1. Calcula la ruta al directorio raíz de tu proyecto (dos niveles arriba de este archivo)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))



@conexion_externa.route("/")
def index():
    
    # Aquí puedes realizar cualquier lógica adicional que necesites
    return render_template("index.html")


@conexion_externa.route("/experiencia")
def experiencia():
    return render_template("experiencia.html")



@conexion_externa.route("/resultado_carga_directo_sheet", methods=["POST"])
def resultado_carga():
    
    sheetId = '1munTyxoLc5px45cz4cO_lLRrqyFsOwjTUh8xDPOiHOg'
    sheet_name = request.form.get("sheet_name")  # recibe del AJAX
    sheet = autenticar_y_abrir_sheet(sheetId, sheet_name)

    if sheet:
        data = sheet.get_all_records()
        completar_publicaciones(data)
        print("Contenido del Sheet:")
       

    # Podés devolver solo un mensaje si es AJAX
    return "Datos cargados correctamente", 200


@conexion_externa.route("/carga_publicacion_en_db/", methods=["POST"])
def carga_publicacion_en_db():
    data = request.get_json()
    sheet_name = data.get("sheet_name")
    fila       = data.get("fila")
    archivoRelacionado = data.get("archivo_relacionado")

    if not fila:
        return "Fila vacía", 400

    try:
        completar_publicaciones([fila])  # debe recibir una lista
        
        ruta = os.path.join(BASE_DIR, "static", "downloads", archivoRelacionado)
        print(f"[DEBUG] Verificando ruta: {ruta} - ¿Existe?: {ruta}", flush=True)

        producto = fila["Producto"]
        validar_publicacion_en_json(ruta, producto)

        return "Fila procesada", 200
    except Exception as e:
        return f"Error {e}", 500



def validar_publicacion_en_json(path_json, nombre_producto):
    """
    Marca como 'TRUE' el campo 'validado' de la publicación cuyo 'Producto' coincida.
    
    Args:
        path_json (str): Ruta al archivo JSON
        nombre_producto (str): Nombre exacto del producto a validar
    """
    try:
        with open(path_json, "r", encoding="utf-8") as f:
            publicaciones = json.load(f)

        modificadas = 0
        for pub in publicaciones:
            if pub.get("Producto") == nombre_producto:
                pub["validado"] = "TRUE"
                modificadas += 1

        if modificadas > 0:
            with open(path_json, "w", encoding="utf-8") as f:
                json.dump(publicaciones, f, ensure_ascii=False, indent=2)
            print(f"✅ {modificadas} publicación(es) actualizada(s) en '{path_json}'")
        else:
            print(f"⚠️ No se encontró ninguna publicación con el producto: '{nombre_producto}'")

    except Exception as e:
        print(f"❌ Error al procesar el archivo JSON: {e}")
