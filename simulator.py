import json
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt

# ---------- Configuration ----------
BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "airq-votrenom-2026"   # MÊME préfixe que dans Wokwi

SPEEDUP = 60          # 1 s réelle = 60 s simulées
PUBLISH_EVERY = 5     # secondes SIMULÉES entre deux pas de calcul
SEND_EVERY_SIM = 300  # une mesure publiée toutes les 5 min simulées
START = datetime(2026, 11, 18, 8, 0, 0)
END = datetime(2026, 11, 18, 18, 0, 0)

C_EXT = 420.0         # ppm
G = 0.005             # L/s par personne


# ---------- Emploi du temps ----------
# (début, fin) en heures décimales : cours, avec pause midi
LESSONS = [(8.5, 10), (10.5, 11.75), (13, 14.5), (14.75, 16.25)]


def in_lesson(hour: float, planning) -> bool:
    return any(a <= hour < b for a, b in planning)


# ---------- Modèle d'une salle ----------
# On définit une classe Room qui représente une salle de classe avec ses caractéristiques et son état.
# Elle contient des méthodes pour mettre à jour l'état de la salle en fonction du temps simulé et pour mesurer les paramètres environnementaux (CO₂, température, humidité) avec un bruit aléatoire pour simuler des capteurs réels.
@dataclass
class Room:
    name: str
    volume: float = 150.0        # m³
    capacity: int = 30
    planning: list = field(default_factory=lambda: LESSONS)
    ventilation_habit: float = 0.5   # 0 = n'aère jamais, 1 = aère souvent

    co2: float = C_EXT
    temp: float = 20.0
    hum: float = 45.0
    window_open_until: float = 0.0   # heure décimale
    occupants: int = 0

    def update(self, sim_time: datetime, dt: float):
        """Avance la salle de dt secondes simulées."""
        hour = sim_time.hour + sim_time.minute / 60 + sim_time.second / 3600

        #Véerfie si l'heure est celle du cours ou non si oui le nombre d'occupants est aléatoire entre 60% et 100% de la capacité sinon il est à 0
        if in_lesson(hour, self.planning):
            if self.occupants == 0:
                self.occupants = random.randint(int(self.capacity * 0.6), self.capacity)
        else:
            self.occupants = 0

        # Aération : un prof ouvre la fenêtre quand ça sent le renfermé
        if self.occupants > 0 and hour >= self.window_open_until:
            threshold = 1500 - 400 * self.ventilation_habit
            if self.co2 > threshold and random.random() < 0.02 * self.ventilation_habit * dt:
                self.window_open_until = hour + random.uniform(5, 10) / 60  # 5 à 10 min

        window_open = hour < self.window_open_until
        # Hors cours, la salle reste fermée (peu de renouvellement)
        lam_per_h = 6.0 if window_open else 1.5   # fuites + portes : plus réaliste que 0.5
        lam = lam_per_h / 3600

        # Bilan de masse du CO₂
        gen = self.occupants * G * 1000 / (self.volume * 1000)  # ppm/s (voir doc)
        dC = gen * 1000 - lam * (self.co2 - C_EXT)
        self.co2 += dC * dt
        self.co2 = max(C_EXT, self.co2)

        # Température : l'occupation chauffe, la fenêtre refroidit
        t_target = 20.0 + 0.06 * self.occupants - (2.0 if window_open else 0.0)
        self.temp += (t_target - self.temp) * min(1.0, dt / 900)

        # Humidité : l'occupation humidifie
        h_target = 42.0 + 0.5 * self.occupants - (4.0 if window_open else 0.0)
        self.hum += (h_target - self.hum) * min(1.0, dt / 900)
#Cette méthode génère les mesures qui ressemblent a celle de vrais capteurs.
#Elle ajoute un petit bruit aléatoire pour rendre les valeurs moins parfaites.
    def measure(self) -> dict:
        """Mesure bruitée, comme un vrai capteur."""
        return {
            "room": self.name,
            "co2": int(round(self.co2 + random.gauss(0, 15))),
            "temp": round(self.temp + random.gauss(0, 0.1), 1),
            "hum": round(min(100, max(0, self.hum + random.gauss(0, 0.5))), 1),
        }


# ---------- Programme principal ----------
#Création des quatre salles.
def main():
    rooms = [
        Room("salle02", volume=150, capacity=30, ventilation_habit=0.9),
        Room("salle03", volume=120, capacity=25, ventilation_habit=0.3),
        Room("salle04", volume=200, capacity=40, ventilation_habit=0.6),
        Room("salle05", volume=90, capacity=20, ventilation_habit=0.0),  # jamais aérée
    ]
    #Transmission MQTT : on se connecte au broker et on publie les mesures toutes les 5 minutes simulées.
    #Cette partie établit une connexion avec le broker MQTT HiveMQ. 
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"sim-{random.randint(0, 99999)}")
    client.connect(BROKER, PORT)
    client.loop_start()

    sim_time = START
    dt = 5.0  # pas de calcul : 5 s simulées
    last_sent = START - timedelta(seconds=SEND_EVERY_SIM)

    print(f"Simulation de {START:%H:%M} à {END:%H:%M} (x{SPEEDUP})")
    while sim_time < END:
        for r in rooms:
            r.update(sim_time, dt)

        if (sim_time - last_sent).total_seconds() >= SEND_EVERY_SIM:
            for r in rooms:
                payload = r.measure()
                payload["ts"] = sim_time.isoformat()
                #Chaque salle publie ses mesures sur un topic différent.
                #Exemple : airq-votrenom-2026/salle02/mesures
                topic = f"{PREFIX}/{r.name}/mesures"
                client.publish(topic, json.dumps(payload))
                print(f"{sim_time:%H:%M} {topic} {payload}")
            last_sent = sim_time

        sim_time += timedelta(seconds=dt)
        time.sleep(dt / SPEEDUP)

    client.loop_stop()
    client.disconnect()
    print("Fin de la journée simulée.")


if __name__ == "__main__":
    main()