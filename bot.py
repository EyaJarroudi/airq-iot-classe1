"""Bot Telegram interactif : /etat donne les dernières mesures de chaque salle."""
import os
import sqlite3
import time

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID"))
API = f"https://api.telegram.org/bot{TOKEN}"
DB = "mesures.db"


def envoyer(texte):
    requests.post(f"{API}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": texte}, timeout=10)


def derniere_mesure_par_salle():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    lignes = con.execute(
        "SELECT room, co2, temp, hum FROM mesures "
        "WHERE id IN (SELECT MAX(id) FROM mesures GROUP BY room) "
        "ORDER BY room").fetchall()
    con.close()
    return lignes


def icone(co2):
    if co2 >= 1500:
        return "🔴"
    if co2 >= 1000:
        return "🟠"
    return "🟢"


def commande_etat():
    lignes = derniere_mesure_par_salle()
    if not lignes:
        return "Aucune mesure en base."
    texte = "État actuel des salles :\n"
    for room, co2, temp, hum in lignes:
        texte += f"{icone(co2)} {room} : {co2:.0f} ppm, {temp:.1f} °C, {hum:.0f} %\n"
    return texte


def main():
    print("Bot démarré (Ctrl+C pour arrêter)")
    offset = None
    while True:
        params = {"timeout": 20}
        if offset:
            params["offset"] = offset
        try:
            r = requests.get(f"{API}/getUpdates", params=params, timeout=30)
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg or str(msg["chat"]["id"]) != CHAT_ID:
                    continue  # on ignore les autres personnes
                if msg.get("text", "").strip().lower().startswith("/etat"):
                    envoyer(commande_etat())
        except requests.RequestException as e:
            print("Erreur réseau :", e)
            time.sleep(5)


if __name__ == "__main__":
    main()