from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("Token chargé :", bool(token), "| longueur :", len(token) if token else 0)
print("Chat ID chargé :", bool(chat_id))