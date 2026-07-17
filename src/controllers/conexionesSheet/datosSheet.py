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

from utils.db import db

import random
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

#import routes.api_externa_conexion.cuenta as cuenta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pprint
import os #obtener el directorio de trabajo actual
import json
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
#load_dotenv(Path('/src/.env'))

#import drive
#drive.mount('/content/gdrive')



datoSheet = Blueprint('datoSheet',__name__)

PAHT_SHEET = os.environ.get('PAHT_SHEET')
PAHT_CREDENTIALS = os.environ.get('PAHT_CREDENTIALS')

BASE_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = BASE_DIR.parent


def resolver_ruta_credencial(path_value):
    if not path_value:
        return None

    candidate = Path(path_value)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    search_roots = [
        Path.cwd(),
        BASE_DIR,
        WORKSPACE_DIR,
    ]

    for root in search_roots:
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return str(resolved)

    return str((WORKSPACE_DIR / candidate).resolve())

newPath = resolver_ruta_credencial(PAHT_CREDENTIALS)
directorio_credenciales = newPath 
autenticado_sheet = False
sheet_manager = False
#SPREADSHEET_ID='1pyPq_2tZJncV3tqOWKaiR_3mt1hjchw12Bl_V8Leh74'#drpiBot2
#SPREADSHEET_ID='1yQeBg8AWinDLaErqjIy6OFn2lp2UM8SRFIcVYyLH4Tg'#drpiBot3 de pruba
SPREADSHEET_ID='1GMv6fwa1-4iwhPBZqY6ZNEVppPeyZY0R4JB39Xmkc5s'#drpiBot de produccion
#1GMv6fwa1-4iwhPBZqY6ZNEVppPeyZY0R4JB39Xmkc5s

precios_data = {}

def login():
    GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = directorio_credenciales
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile(directorio_credenciales)
    
    if gauth.credentials is None:
        gauth.LocalWebserverAuth(port_numbers=[8092])
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
        
    gauth.SaveCredentialsFile(directorio_credenciales)
    credenciales = GoogleDrive(gauth)
    return credenciales

def autenticar_y_abrir_sheet(sheetId, sheet_name):
    print("[DEBUG] Entrando a autenticar_y_abrir_sheet", flush=True)
    try:
        scope = ['https://spreadsheets.google.com/feeds', 
                 'https://www.googleapis.com/auth/drive']
        newPath = resolver_ruta_credencial(PAHT_SHEET)
        
       # print(f"[DEBUG] cwd: {os.getcwd()}", flush=True)
        print(f"[DEBUG] buscando credenciales en: {newPath}", flush=True)
       # print(f"[DEBUG] existe?: {os.path.exists(newPath)}", flush=True)
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(newPath, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheetId).worksheet(sheet_name)  # Abre el sheet especificado
      
        print(f"[DEBUG] hoja abierta correctamente: {sheet.title}", flush=True)
        return sheet
    except Exception as e:
        print(f"[ERROR] Error al autenticar y abrir la hoja: {e}", flush=True)
        return None  # Puedes devolver None o manejar de otra manera el error en tu aplicación




def actualizar_estado_en_sheet(sheet, fila_idx_list: list[int], col_name: str = "validado"):
    header = sheet.row_values(1)

    try:
        col_idx = header.index(col_name) + 1
    except ValueError:
        raise RuntimeError(f"Columna '{col_name}' no existe")

    for row_idx in fila_idx_list:
        if not isinstance(row_idx, int):
            raise ValueError(f"Se esperaba un número de fila, pero se recibió: {type(row_idx)} → {row_idx}")

        print(f"✅ Actualizando fila {row_idx}, columna '{col_name}' (índice {col_idx}) → 'TRUE'")
        sheet.update_cell(row_idx, col_idx, "TRUE")

      
       












#def leerSheet_arbitrador001(): 

def leerSheet(sheetId,sheet_name): 
        global autenticado_sheet, sheet_manager
        if not autenticado_sheet:        
            # recibo la tupla pero como este es para el bot leo el primer elemento 
          
            credentials_path = resolver_ruta_credencial(PAHT_SHEET)
            # Crear instancia del gestor de hojas
            sheet_manager = GoogleSheetManager(credentials_path)

            if sheet_manager.autenticar():
                autenticado_sheet = True
                handler = SheetHandler(sheet_manager, sheetId, sheet_name)
        else:
            # Autenticar
            if  autenticado_sheet:
                # Crear instancia del manejador de hoja con el gestor y los datos de la hoja
                handler = SheetHandler(sheet_manager, sheetId, sheet_name)
            else:
                    print("Error al autenticar. Revisa los detalles del error.")
                    autenticado_sheet = False
                    return render_template('notificaciones/noPoseeDatos.html',layout = 'layout_fichas')    
                
                # Ejemplo de uso de leerSheet
        return handler.leerSheet()
    
    
    
    