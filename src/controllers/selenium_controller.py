from flask import Blueprint
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Crear un Blueprint para manejar las rutas
selenium_controller = Blueprint('selenium_controller', __name__)

@selenium_controller.route('/selenium_home/')
def selenium_home():
    # Crear opciones para Chrome
    options = Options()
    options.add_argument("--headless")  # Ejecutar en modo headless (sin interfaz gráfica)
    options.add_argument("--no-sandbox")  # Solución para errores en contenedores
    options.add_argument("--disable-dev-shm-usage")  # Solución para contenedores con poca memoria compartida

    # Configura el driver de Chrome utilizando Selenium y WebDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Abre una página web
    driver.get("https://www.google.com")

    # Obtén el título de la página
    page_title = driver.title

    # Cierra el navegador
    driver.quit()

    return f'Página abierta: {page_title}'
