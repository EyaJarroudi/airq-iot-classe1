# Surveillance simulée de la qualité de l'air en salle de classe

Chaîne IoT 100 % simulée : ESP32 (Wokwi) + simulateur Python, MQTT, SQLite, Grafana, alerte Telegram.

## Lien Wokwi

<<<<<<< HEAD
(https://wokwi.com/projects/481303302134062081)

=======
[(https://wokwi.com/projects/481303302134062081)]
>>>>>>> e23b44abf350eddf73508415593577e41084675f
## Lancement

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
