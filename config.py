import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL       = os.getenv("CARDVAULT_API_URL", "http://localhost:5000/api").rstrip("/")
API_USERNAME       = os.getenv("CARDVAULT_API_USERNAME", "")
API_PASSWORD       = os.getenv("CARDVAULT_API_PASSWORD", "")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN no configurado en .env")
if not API_USERNAME or not API_PASSWORD:
    raise RuntimeError("CARDVAULT_API_USERNAME y CARDVAULT_API_PASSWORD son obligatorios en .env")
