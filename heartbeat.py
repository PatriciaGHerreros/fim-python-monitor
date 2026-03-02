import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_latido():
    fecha = datetime.now().strftime("%d/%m/%Y")
    mensaje = (
        f"💓 **Heartbeat: Tu guardián está activo**\n"
        f"📅 Fecha: {fecha}\n"
        f"🛡️ Estado: Vigilancia HDS operando normalmente.\n"
        f"✨ _'Aquí sigo, cuidando de tu negocio.'_"
    )
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Latido enviado con éxito.")
        else:
            print(f"⚠️ Telegram respondió con error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    enviar_latido()
