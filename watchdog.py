"""Watchdog : détecte les salles muettes et les valeurs aberrantes,
et envoie une alerte Telegram à chaque changement d'état."""
import os
import sqlite3
import time

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB = "mesures.db"
SALLES = ["salle01", "salle02", "salle03", "salle04", "salle05"]
SILENCE_S = 30
LIMITES = {
    "co2": (300, 5000),
    "temp": (-10, 50),
    "hum": (0, 100),
}
PERIODE_S = 10


def envoyer(texte):
    """Envoie un message Telegram (sans planter le watchdog si le réseau échoue)."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": texte}, timeout=10)
    except requests.RequestException as e:
        print("Envoi Telegram impossible :", e)


def dernieres_mesures():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    lignes = con.execute(
        "SELECT room, co2, temp, hum, ts_epoch FROM mesures "
        "WHERE id IN (SELECT MAX(id) FROM mesures GROUP BY room)"
    ).fetchall()
    con.close()
    return {l[0]: l[1:] for l in lignes}


def verifier():
    """Retourne un dictionnaire {clé_stable: texte} des problèmes actuels."""
    problemes = {}
    mesures = dernieres_mesures()
    maintenant = time.time()
    for salle in SALLES:
        if salle not in mesures:
            problemes[(salle, "absente")] = f"{salle} : aucune mesure en base"
            continue
        co2, temp, hum, ts = mesures[salle]
        if ts > 1e11:
            ts = ts / 1000
        silence = maintenant - ts
        if silence > SILENCE_S:
            problemes[(salle, "silence")] = f"{salle} : SILENCE depuis {silence:.0f} s"
        for nom, valeur in (("co2", co2), ("temp", temp), ("hum", hum)):
            mini, maxi = LIMITES[nom]
            if valeur is None or not (mini <= valeur <= maxi):
                problemes[(salle, nom)] = f"{salle} : {nom} ABERRANT ({valeur})"
    return problemes


if __name__ == "__main__":
    print("Watchdog démarré (Ctrl+C pour arrêter)")
    deja_signales = {}   # {clé: texte} des pannes déjà annoncées
    while True:
        actuels = verifier()
        heure = time.strftime("%H:%M:%S")

        for cle, texte in actuels.items():
            if cle not in deja_signales:            # nouvelle panne
                print(f"[{heure}] NOUVELLE PANNE : {texte}")
                envoyer(f"⚠️ PANNE CAPTEUR\n{texte}")
        for cle, texte in deja_signales.items():
            if cle not in actuels:                  # panne résolue
                print(f"[{heure}] RÉSOLU : {cle[0]} ({cle[1]})")
                envoyer(f"✅ RÉTABLI : {cle[0]} ({cle[1]}) est de nouveau normal")

        deja_signales = actuels
        if not actuels:
            print(f"[{heure}] OK : 5 salles actives, valeurs plausibles")
        time.sleep(PERIODE_S)