# Surveillance simulée de la qualité de l'air en salle de classe

Chaîne IoT 100 % simulée : ESP32 (Wokwi) + simulateur Python, MQTT, SQLite, Grafana, alerte Telegram.

## Lien Wokwi

(https://wokwi.com/projects/481303302134062081)

1. `python -m venv venv` puis `venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Lancer Wokwi (Start)
4. `python collector.py`
5. `python simulator.py`
6. `docker compose up -d`, puis ouvrir http://localhost:3001

## Fichiers

- `simulator.py` : salles 02 à 05 (modèle de CO2)
- `collector.py` : MQTT vers SQLite
- `docker-compose.yml` : Grafana + plugin SQLite
- `grafana/dashboard.json` : dashboard exporté
## Fonctionnalités avancées

### Watchdog (surveillance des capteurs)
`python watchdog.py` détecte :
- les salles muettes (aucune mesure depuis 30 s),
- les valeurs aberrantes (CO₂ hors 300-5000 ppm, température hors -10/50 °C, humidité hors 0-100 %).
Une alerte Telegram est envoyée à chaque panne et à chaque rétablissement (pas de spam).

### Bot Telegram interactif
`python bot.py` répond aux commandes :
- `/etat` : dernière mesure de chaque salle
- `/salleNN` : détail d'une salle (ex. `/salle03`)
Le bot ne répond qu'au chat autorisé (TELEGRAM_CHAT_ID).

## Configuration
Copier `.env.example` en `.env` et renseigner TELEGRAM_TOKEN et TELEGRAM_CHAT_ID.

## Ordre de lancement
1. Wokwi (Start)  2. `python collector.py`  3. `python simulator.py`
4. `python watchdog.py`  5. `python bot.py`