import json
import sqlite3
import time
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "airq-votrenom-2026"      # MÊME préfixe que partout
TOPIC = f"{PREFIX}/+/mesures"
DB_FILE = "mesures.db"


def init_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_FILE)  #crée le fichier "mesures.db" s'il n'existe pas
    db.execute("""
        CREATE TABLE IF NOT EXISTS mesures (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        room      TEXT    NOT NULL,
        co2       INTEGER,
        temp      REAL,
        hum       REAL,
        ts_sim    TEXT,
        ts_recv   TEXT NOT NULL,
        ts        TEXT NOT NULL,
        ts_epoch  INTEGER NOT NULL   -- heure réelle en secondes (UTC)
    )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_room_epoch ON mesures(room, ts_epoch)")
    db.commit()
    return db


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connecté au broker (code {reason_code})")
    client.subscribe(TOPIC)          # réabonnement automatique après coupure
    print(f"Abonné à {TOPIC}")


def on_message(client, userdata, msg):
    db = userdata
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        room = str(data["room"])
        co2 = int(data["co2"])
        temp = float(data["temp"])
        hum = float(data["hum"])
    except (ValueError, KeyError, TypeError) as e:
        print(f"Message ignoré ({e}) : {msg.payload[:80]!r}")
        return

    ts_recv = datetime.now().isoformat(timespec="seconds")
    ts_sim = data.get("ts")
    ts = ts_sim or ts_recv

    db.execute(
        "INSERT INTO mesures (room, co2, temp, hum, ts_sim, ts_recv, ts, ts_epoch) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (room, co2, temp, hum, ts_sim, ts_recv, ts,int(time.time())),
    )
    db.commit()
    print(f"[{ts}] {room}: CO2={co2} T={temp} H={hum}")


def main():
    db = init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"collector-{int(time.time())}",
                         userdata=db)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Arrêt du collecteur.")
    finally:
        client.disconnect()
        db.close()


if __name__ == "__main__":
    main()