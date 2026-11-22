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

def commande_salle(nom):
    """Détail d'une salle : dernière mesure + ancienneté."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ligne = con.execute(
        "SELECT co2, temp, hum, ts_epoch FROM mesures "
        "WHERE room = ? ORDER BY id DESC LIMIT 1", (nom,)).fetchone()
    con.close()
    if ligne is None:
        return (f"Salle inconnue : {nom}\n"
                "Essayez /etat pour voir les salles disponibles.")
    co2, temp, hum, ts = ligne
    if ts > 1e11:
        ts = ts / 1000
    age = time.time() - ts
    texte = (f"{icone(co2)} {nom}\n"
             f"CO₂ : {co2:.0f} ppm\n"
             f"Température : {temp:.1f} °C\n"
             f"Humidité : {hum:.0f} %\n"
             f"Dernière mesure : il y a {age:.0f} s")
    if age > 30:
        texte += "\n⚠️ Cette salle semble muette."
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
                texte_recu = msg.get("text", "").strip().lower()
                if texte_recu.startswith("/etat"):
                    envoyer(commande_etat())
                elif texte_recu.startswith("/salle"):
                    nom = texte_recu[1:].split("@")[0].split()[0]
                    envoyer(commande_salle(nom))
        except requests.RequestException as e:
            print("Erreur réseau :", e)
            time.sleep(5)


if __name__ == "__main__":
    main()