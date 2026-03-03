import os
import hashlib
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def calcular_hash(ruta):
    sha256 = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(4096), b""):
            sha256.update(bloque)
    return sha256.hexdigest()

def crear_inventario(carpeta):
    inventario = {}
    for raiz, _, archivos in os.walk(carpeta):
        if any(excluir in raiz for excluir in ["backups_seguros", "cuarentena", ".git"]):
            continue
        for nombre in archivos:
            if nombre == "baseline.json": continue
            ruta_completa = os.path.join(raiz, nombre)
            inventario[ruta_completa] = calcular_hash(ruta_completa)
    
    with open("baseline.json", "w") as f:
        json.dump(inventario, f, indent=4)
    return inventario

def comparar(carpeta):
    if not os.path.exists("baseline.json"):
        return
    
    with open("baseline.json", "r") as f:
        baseline = json.load(f)
    
    actual = {}
    for raiz, _, archivos in os.walk(carpeta):
        if any(excluir in raiz for excluir in ["backups_seguros", "cuarentena", ".git"]):
            continue
        for nombre in archivos:
            if nombre == "baseline.json": continue
            ruta_completa = os.path.join(raiz, nombre)
            actual[ruta_completa] = calcular_hash(ruta_completa)

    mensajes = []
    for ruta, hash_antiguo in baseline.items():
        if ruta not in actual:
            mensajes.append(f"❌ **BORRADO:** {ruta}")
        elif actual[ruta] != hash_antiguo:
            mensajes.append(f"🚨 **MODIFICADO:** {ruta}")
    
    for ruta in actual:
        if ruta not in baseline:
            mensajes.append(f"⚠️ **NUEVO:** {ruta}")

    if mensajes:
        texto = "\n".join(mensajes)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": f"🛡️ **ALERTA HDS**\n\n{texto}", "parse_mode": "Markdown"})
    else:
        # En GitHub solo avisamos si hay cambios. En local mandamos OK.
        if not os.getenv("GITHUB_ACTIONS"):
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Todo en orden."})

def revisar_una_vez(carpeta):
    if not os.path.exists("baseline.json"):
        crear_inventario(carpeta)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                     data={"chat_id": CHAT_ID, "text": "✅ **Vigilancia Programada:** Entorno sincronizado.", "parse_mode": "Markdown"})
    else:
        comparar(carpeta)

if __name__ == "__main__":
    if os.getenv("GITHUB_ACTIONS"):
        revisar_una_vez(".")
    else:
        revisar_una_vez("/home/horizontedigitalseguro/HDS-web")