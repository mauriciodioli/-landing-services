
from models.popupsm.popup import Popup
from models.campania_contacto import CampaniaContacto
from models.campania_telefonica import CampaniaTelefonica
from models.contacto_telefonico import ContactoTelefonico
from models.historial_contacto import HistorialContacto
from extensions import db as app_db


from datetime import datetime
from flask import Blueprint,flash

create_tablas = Blueprint('create_tablas',__name__)

def crea_tablas_DB():
    Popup.crear_tabla_popup()
    app_db.create_all()
   
    flash('Tablas creadas exitosamente', 'success')
    print('tablas creadas exitosamente')
    
    
    
    
    
    
    
   
    