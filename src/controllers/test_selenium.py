from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

# Filtrar solo los productos que tienen link válido de AliExpress
df_ali = df_articulos[df_articulos['Proveedor más barato'] == 'AliExpress'].copy()

# Inicializar Selenium en modo headless
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=chrome_options)

# Función para extraer imágenes desde una página de producto AliExpress
def extraer_imagenes_aliexpress(url, max_imgs=6):
    try:
        driver.get(url)
        time.sleep(4)
        html = driver.page_source
        img_urls = list(set(re.findall(r'https://ae[-\w\.]+/kf/\S+?\.(jpg|jpeg|png)', html)))
        img_urls = [img for img in img_urls if '_.webp' not in img][:max_imgs]
        return img_urls + [""] * (max_imgs - len(img_urls))  # completar hasta 6
    except Exception:
        return [""] * max_imgs

# Extraer imágenes para cada producto
imagenes_totales = []
for link in df_ali["Link del proveedor"]:
    imgs = extraer_imagenes_aliexpress(link)
    imagenes_totales.append(imgs)

# Cargar en el DataFrame
for i in range(6):
    df_ali[f"imagen{i+1}"] = [imgs[i] for imgs in imagenes_totales]

driver.quit()

# Guardar archivo enriquecido
csv_output_path = "/mnt/data/productos_polonia_con_imagenes.csv"
df_ali.to_csv(csv_output_path, index=False)


csv_output_path
