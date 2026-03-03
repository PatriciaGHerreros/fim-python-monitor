import hashlib
import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import shutil

# Cargamos el Token y el ID desde el archivo .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- FUNCIONES DE APOYO ---

def enviar_telegram(mensaje):
    """Envía una notificación push al móvil del analista vía Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"🛡️ ALERTA DE SEGURIDAD 🛡️\n\n{mensaje}",
        "parse_mode": "Markdown" # Para que las negritas de Telegram funcionen
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

def calcular_hash(ruta_archivo):
    """Calcula la huella digital SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    try:
        with open(ruta_archivo, "rb") as f:
            for bloque in iter(lambda: f.read(4096), b""):
                sha256_hash.update(bloque)
        return sha256_hash.hexdigest()
    except Exception:
        return None

def registrar_alerta(mensaje):
    """Escribe eventos en el log y los envía a Telegram."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea_log = f"[{timestamp}] {mensaje}\n"
    with open("registro_seguridad.txt", "a", encoding="utf-8") as f:
        f.write(linea_log)
    enviar_telegram(mensaje)

# --- GESTIÓN DEL INVENTARIO (BASELINE) ---

def crear_inventario(carpeta):
    """Crea el baseline y guarda una copia física de seguridad."""
    inventario = {}
    if not os.path.exists(carpeta):
        print(f"❌ Error: La carpeta '{carpeta}' no existe.")
        return

    print("📦 Asegurando archivos originales...")
    for nombre_archivo in os.listdir(carpeta):
        ruta_completa = os.path.join(carpeta, nombre_archivo)
        if os.path.isfile(ruta_completa):
            # Ignorar base de datos en inventario inicial
            if ruta_completa.endswith(".sqlite3"): continue

            hash_val = calcular_hash(ruta_completa)
            if hash_val:
                inventario[ruta_completa] = hash_val
                realizar_backup_limpio(ruta_completa)

    with open("baseline.json", "w", encoding="utf-8") as f:
        json.dump(inventario, f, indent=4)
    print("✅ Inventario y Backups creados con éxito.")

def realizar_backup_limpio(ruta_origen):
    """Copia el archivo original a backups_seguros."""
    if not os.path.exists("backups_seguros"):
        os.makedirs("backups_seguros")
    nombre_archivo = os.path.basename(ruta_origen)
    ruta_destino = f"backups_seguros/{nombre_archivo}"
    shutil.copy2(ruta_origen, ruta_destino)

def realizar_copia_seguridad(ruta_archivo):
    """Copia el archivo modificado a cuarentena."""
    if not os.path.exists("cuarentena"):
        os.makedirs("cuarentena")
    nombre_base = os.path.basename(ruta_archivo)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_destino = f"cuarentena/{timestamp}_{nombre_base}"
    try:
        shutil.copy2(ruta_archivo, ruta_destino)
        return ruta_destino
    except:
        return "Error en copia"

# --- LÓGICA DE MONITOREO ---

def monitorear(carpeta):
    """Modo persistente (Bucle infinito) para Servidores."""
    if not os.path.exists("baseline.json"):
        crear_inventario(carpeta)

    with open("baseline.json", "r", encoding="utf-8") as f:
        baseline = json.load(f)

    total_archivos = len(baseline)
    registrar_alerta(f"✅ **Monitor Persistente Iniciado**\n📂 Carpeta: `{carpeta}`\n📄 Archivos: {total_archivos}")

    try:
        while True:
            time.sleep(10)
            ejecutar_logica_revision(carpeta, baseline)
            # Guardamos el estado por si hay cambios
            with open("baseline.json", "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=4)
    except KeyboardInterrupt:
        print("\n🛑 Detenido.")

def revisar_una_vez(carpeta):
    """Versión optimizada para GitHub Actions (Evita spam de 'Nuevos')"""
    if not os.path.exists("baseline.json"):
        print("🤖 Entorno nuevo detectado. Creando baseline silencioso...")
        crear_inventario(carpeta)
        # En GitHub, no queremos que el primer escaneo llene Telegram de 'Nuevos'
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": "✅ **Vigilancia Programada:** Entorno sincronizado y verificado.",
            "parse_mode": "Markdown"
        }
        requests.post(url, data=payload)
        return

    # Si ya existe el baseline (porque lo subiste con git add -f), compara normal
    comparar(carpeta)

def ejecutar_logica_revision(carpeta, baseline):
    """Lógica compartida de detección de cambios."""
    archivos_actuales = os.listdir(carpeta)
    rutas_actuales = [os.path.join(carpeta, f) for f in archivos_actuales]

    # 1. Nuevos y Modificados
    for ruta in rutas_actuales:
        if os.path.isfile(ruta):
            if ruta.endswith(".sqlite3") or "-journal" in ruta: continue

            hash_actual = calcular_hash(ruta)
            if not hash_actual: continue

            if ruta not in baseline:
                msg = f"[⚠️ NUEVO] Detectado: `{ruta}`"
                print(msg)
                registrar_alerta(msg)
                baseline[ruta] = hash_actual
            elif hash_actual != baseline[ruta]:
                ruta_bak = realizar_copia_seguridad(ruta)
                msg = f"[🚨 ALERTA] Modificado: `{ruta}`\n📂 Cuarentena: `{ruta_bak}`"
                print(msg)
                registrar_alerta(msg)
                baseline[ruta] = hash_actual

    # 2. Eliminados
    for ruta_reg in list(baseline.keys()):
        if not os.path.exists(ruta_reg):
            msg = f"[❌ BORRADO] Eliminado: `{ruta_reg}`"
            print(msg)
            registrar_alerta(msg)
            del baseline[ruta_reg]

# --- INICIO DEL PROGRAMA ---

if __name__ == "__main__":
    # Detectar entorno
    if os.getenv("GITHUB_ACTIONS"):
        # En GitHub vigilamos el repo actual
        revisar_una_vez(".")
    else:
        # En PythonAnywhere vigilamos tu web
        ruta_web = "/home/horizontedigitalseguro/HDS-web"
        monitorear(ruta_web)