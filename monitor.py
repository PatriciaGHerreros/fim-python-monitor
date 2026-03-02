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

# PRUEBA DE DIAGNÓSTICO:
print(f"DEBUG: El token cargado es: {TOKEN}")
print(f"DEBUG: El ID cargado es: {CHAT_ID}")

# --- FUNCIONES DE APOYO ---

def enviar_telegram(mensaje):
    """Envía una notificación push al móvil del analista vía Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"🛡️ ALERTA DE SEGURIDAD 🛡️\n\n{mensaje}"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

def calcular_hash(ruta_archivo):
    """Calcula la huella digital SHA-256 de un archivo para verificar su integridad."""
    sha256_hash = hashlib.sha256()
    try:
        with open(ruta_archivo, "rb") as f:
            for bloque in iter(lambda: f.read(4096), b""):
                sha256_hash.update(bloque)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None

def registrar_alerta(mensaje):
    """Escribe eventos en el log y los envía a Telegram."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea_log = f"[{timestamp}] {mensaje}\n"
    # 1. Guardar en log local
    with open("registro_seguridad.txt", "a", encoding="utf-8") as f:
        f.write(linea_log)
    
    # 2. Notificar al analista
    enviar_telegram(mensaje)

# --- GESTIÓN DEL INVENTARIO (BASELINE) ---

def crear_inventario(carpeta):
    """Crea el baseline y guarda una copia física de seguridad de cada archivo."""
    inventario = {}
    if not os.path.exists(carpeta):
        print(f"❌ Error: La carpeta '{carpeta}' no existe.")
        return

    print("📦 Asegurando archivos originales...")
    for nombre_archivo in os.listdir(carpeta):
        ruta_completa = os.path.join(carpeta, nombre_archivo)
        if os.path.isfile(ruta_completa):
            # 1. Calculamos el hash
            inventario[ruta_completa] = calcular_hash(ruta_completa)
            # 2. Hacemos la copia de seguridad limpia
            realizar_backup_limpio(ruta_completa)
    
    with open("baseline.json", "w", encoding="utf-8") as f:
        json.dump(inventario, f, indent=4)
    print("✅ Inventario y Backups limpios creados con éxito.")

def realizar_backup_limpio(ruta_origen):
    """Crea una copia del archivo original cuando el sistema está limpio."""
    if not os.path.exists("backups_seguros"):
        os.makedirs("backups_seguros")
    
    nombre_archivo = os.path.basename(ruta_origen)
    ruta_destino = f"backups_seguros/{nombre_archivo}"
    
    shutil.copy2(ruta_origen, ruta_destino)
    return ruta_destino

# --- LÓGICA PRINCIPAL DE VIGILANCIA ---

def monitorear(carpeta):
    """Vigila la carpeta, mantiene un log auditable y realiza copias de seguridad de cambios."""
    
    # 1. Cargamos el estado seguro conocido
    if not os.path.exists("baseline.json"):
        print("❌ Error: No existe el archivo baseline.json. Créalo primero.")
        return

    with open("baseline.json", "r", encoding="utf-8") as f:
        baseline = json.load(f)

    print(f"--- 🛡️ VIGILANCIA ACTIVA EN: {carpeta} ---")
    print(f"--- 📝 REGISTRO DE EVENTOS EN: registro_seguridad.txt ---")
    registrar_alerta("SISTEMA INICIADO: Comienza la monitorización.")

    try:
        while True:
            time.sleep(5)  # Pausa para optimizar el uso de CPU
            
            # 2. Comprobamos archivos actuales (Nuevos o Modificados)
            archivos_actuales = os.listdir(carpeta)
            rutas_actuales = [os.path.join(carpeta, f) for f in archivos_actuales]

            for ruta in rutas_actuales:
                if os.path.isfile(ruta):
                    hash_actual = calcular_hash(ruta)

                    # CASO A: El archivo es nuevo
                    if ruta not in baseline:
                        msj = f"[⚠️ NUEVO] Archivo detectado: {ruta}"
                        print(msj)
                        registrar_alerta(msj)
                        baseline[ruta] = hash_actual 
                    
                    # CASO B: El archivo ha sido modificado
                    elif hash_actual != baseline.get(ruta):
                        # --- MEJORA PARA EMPRENDEDORAS: COPIA DE SEGURIDAD ---
                        ruta_backup = realizar_copia_seguridad(ruta)
                        
                        msj = (f"[🚨 ALERTA] ¡CONTENIDO MODIFICADO!: {ruta}\n"
                               f"📂 Backup creado en: {ruta_backup}")
                        
                        print(msj)
                        registrar_alerta(msj) # Esto lo guarda en log y lo envía a Telegram
                        baseline[ruta] = hash_actual

            # 3. Comprobamos archivos eliminados
            for ruta_registrada in list(baseline.keys()):
                if not os.path.exists(ruta_registrada):
                    msj = f"[❌ BORRADO] El archivo ya no existe: {ruta_registrada}"
                    print(msj)
                    registrar_alerta(msj)
                    del baseline[ruta_registrada] 

    except KeyboardInterrupt:
        print("\n🛑 Vigilancia detenida por el usuario.")


# --- COPIA DE SEGURIDAD ---     
def realizar_copia_seguridad(ruta_archivo):
    """Copia el archivo modificado a una carpeta de cuarentena para análisis."""
    if not os.path.exists("cuarentena"):
        os.makedirs("cuarentena")
    
    nombre_base = os.path.basename(ruta_archivo)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_destino = f"cuarentena/{timestamp}_{nombre_base}"
    
    try:
        shutil.copy2(ruta_archivo, ruta_destino)
        return ruta_destino
    except Exception as e:
        return f"Error al copiar: {e}"   

# --- INICIO DEL PROGRAMA ---

if __name__ == "__main__":
    carpeta_objetivo = "archivos_criticos"
    
    # IMPORTANTE:
    # 1. Descomenta la línea de abajo la PRIMERA VEZ o cuando hagas cambios legítimos.
    # 2. Vuelve a comentarla para que el script solo MONITOREE.
    
    # crear_inventario(carpeta_objetivo)
    
    monitorear(carpeta_objetivo)