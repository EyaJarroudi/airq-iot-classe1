#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

#define DHT_PIN 15
#define DHT_TYPE DHT22
#define CO2_PIN 34

const char *WIFI_SSID = "Wokwi-GUEST"; // réseau WiFi simulé de Wokwi
const char *WIFI_PASS = "";
const char *MQTT_HOST = "broker.hivemq.com";
const int MQTT_PORT = 1883;
// Préfixe unique pour éviter les collisions sur le broker public
const char *TOPIC = "airq-votrenom-2026/salle01/mesures";

WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(DHT_PIN, DHT_TYPE);

void connectWifi()
{
    Serial.print("WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASS, 6); // canal 6 = connexion plus rapide
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(250);
        Serial.print(".");
    }
    Serial.println(" OK");
}

void connectMqtt()
{
    while (!mqtt.connected())
    {
        String id = "esp32-salle01-" + String(random(0xffff), HEX);
        Serial.print("MQTT...");
        if (mqtt.connect(id.c_str()))
        {
            Serial.println(" OK");
        }
        else
        {
            Serial.printf(" echec rc=%d\n", mqtt.state());
            delay(2000);
        }
    }
}

void setup()
{
    Serial.begin(115200);
    dht.begin();
    connectWifi();
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop()
{
    if (!mqtt.connected())
        connectMqtt();
    mqtt.loop();

    static unsigned long last = 0;
    if (millis() - last < 5000)
        return; // une mesure toutes les 5 s
    last = millis();

    float t = dht.readTemperature();
    float h = dht.readHumidity();
    int raw = analogRead(CO2_PIN);          // 0..4095
    int co2 = map(raw, 0, 4095, 400, 2000); // ppm simulés

    if (isnan(t) || isnan(h))
    {
        Serial.println("Erreur lecture DHT22");
        return;
    }

    JsonDocument doc;
    doc["room"] = "salle01";
    doc["co2"] = co2;
    doc["temp"] = round(t * 10) / 10.0;
    doc["hum"] = round(h * 10) / 10.0;

    char payload[160];
    serializeJson(doc, payload);
    mqtt.publish(TOPIC, payload);
    Serial.println(payload);
}