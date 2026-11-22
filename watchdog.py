"""Watchdog : détecte les salles muettes et les valeurs aberrantes."""
import sqlite3
import time

DB = "mesures.db"
SALLES = ["salle01", "salle02", "salle03", "salle04", "salle05"]
SILENCE_S = 30          # secondes réelles sans mesure => panne
# 1 mesure / 5 s réelles (5 min simulées à x60) => 30 s = environ 6 mesures manquées
LIMITES = {             # plages physiquement plausibles
    "co2": (300, 5000),
    "temp": (-10, 50),
    "hum": (0, 100),
}
PERIODE_S = 10          # on vérifie toutes les 10 s


def dernieres_mesures():
    """Dernière mesure de chaque salle (base ouverte en lecture seule)."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    lignes = con.execute(
        "SELECT room, co2, temp, hum, ts_epoch FROM mesures "
        "WHERE id IN (SELECT MAX(id) FROM mesures GROUP BY room)"
    ).fetchall()
    con.close()
    return {l[0]: l[1:] for l in lignes}


def verifier():
    """Retourne la liste des problèmes détectés (texte)."""
    problemes = []
    mesures = dernieres_mesures()
    maintenant = time.time()
    for salle in SALLES:
        if salle not in mesures:
            problemes.append(f"{salle} : aucune mesure en base")
            continue
        co2, temp, hum, ts = mesures[salle]
        if ts > 1e11:           # au cas où ts_epoch serait en millisecondes
            ts = ts / 1000
        silence = maintenant - ts
        if silence > SILENCE_S:
            problemes.append(f"{salle} : SILENCE depuis {silence:.0f} s")
        for nom, valeur in (("co2", co2), ("temp", temp), ("hum", hum)):
            mini, maxi = LIMITES[nom]
            if valeur is None or not (mini <= valeur <= maxi):
                problemes.append(f"{salle} : {nom} ABERRANT ({valeur})")
    return problemes


if __name__ == "__main__":
    print("Watchdog démarré (Ctrl+C pour arrêter)")
    while True:
        problemes = verifier()
        heure = time.strftime("%H:%M:%S")
        if problemes:
            for p in problemes:
                print(f"[{heure}] PANNE : {p}")
        else:
            print(f"[{heure}] OK : 5 salles actives, valeurs plausibles")
        time.sleep(PERIODE_S)