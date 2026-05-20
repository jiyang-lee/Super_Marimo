#ifndef __has_include
#define __has_include(x) 0
#endif

#include <Arduino.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>

#if __has_include(<DHT.h>)
#include <DHT.h>
#define WEMOS_HAS_DHT 1
#else
#define WEMOS_HAS_DHT 0
#endif

#if __has_include("config.h")
#include "config.h"
#endif

#ifndef WIFI_SSID
#define WIFI_SSID "CHANGE_ME"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "CHANGE_ME"
#endif
#ifndef API_BASE_URL
#define API_BASE_URL "http://192.168.0.10:8000"
#endif
#ifndef DEVICE_ID
#define DEVICE_ID "wemos"
#endif
#ifndef SENSOR_INTERVAL_MS
#define SENSOR_INTERVAL_MS 3000UL
#endif
#ifndef LIGHT_PIN
#define LIGHT_PIN A0
#endif
#ifndef TRIG_PIN
#define TRIG_PIN D5
#endif
#ifndef ECHO_PIN
#define ECHO_PIN D6
#endif
#ifndef DHT_PIN
#define DHT_PIN D2
#endif
#ifndef DHT_TYPE
#define DHT_TYPE DHT22
#endif
#ifndef WATER_FULL_DISTANCE_CM
#define WATER_FULL_DISTANCE_CM 20.0f
#endif
#ifndef WATER_EMPTY_DISTANCE_CM
#define WATER_EMPTY_DISTANCE_CM 60.0f
#endif

#if WEMOS_HAS_DHT
DHT dht(DHT_PIN, DHT_TYPE);
#endif

struct SensorSnapshot {
  float light = 0.0f;
  float distance = 0.0f;
  float temperature = 0.0f;
  float humidity = 0.0f;
  float water_level = 0.0f;
  int water_raw = 0;
  int light_raw = 0;
};

static SensorSnapshot last_snapshot = {
    420.0f,
    18.0f,
    24.5f,
    52.0f,
    61.0f,
    610,
    420,
};
static unsigned long last_tick_at = 0;
static unsigned long last_hourly_at = 0;
static unsigned long last_wifi_check_at = 0;
static unsigned long last_wifi_log_at = 0;

static String buildUrl(const char *path) {
  String base = String(API_BASE_URL);
  while (base.endsWith("/")) {
    base.remove(base.length() - 1);
  }
  return base + String(path);
}

static bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[wifi] connecting to %s\n", WIFI_SSID);
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000UL) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] connect failed");
    return false;
  }
  Serial.printf("[wifi] connected ip=%s\n", WiFi.localIP().toString().c_str());
  return true;
}

static void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  if (millis() - last_wifi_check_at < 5000UL) {
    return;
  }

  last_wifi_check_at = millis();
  if (!connectWiFi()) {
    if (millis() - last_wifi_log_at >= 15000UL) {
      last_wifi_log_at = millis();
      Serial.println("[wifi] retry scheduled while keeping sensor loop alive");
    }
  }
}

static float readLightRaw() {
  return static_cast<float>(analogRead(LIGHT_PIN));
}

static float readDistanceCm() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) {
    return last_snapshot.distance > 0.0f ? last_snapshot.distance : 35.0f;
  }
  return static_cast<float>(duration) * 0.0343f / 2.0f;
}

static void readEnvironment(float &temperature, float &humidity) {
#if WEMOS_HAS_DHT
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  if (!isnan(temp)) {
    temperature = temp;
  } else {
    temperature = last_snapshot.temperature;
  }
  if (!isnan(hum)) {
    humidity = hum;
  } else {
    humidity = last_snapshot.humidity;
  }
#else
  temperature = last_snapshot.temperature;
  humidity = last_snapshot.humidity;
#endif
}

static float computeWaterLevelPercent(float distanceCm) {
  float span = WATER_EMPTY_DISTANCE_CM - WATER_FULL_DISTANCE_CM;
  if (span <= 0.0f) {
    return 0.0f;
  }
  float pct = (WATER_EMPTY_DISTANCE_CM - distanceCm) * 100.0f / span;
  if (pct < 0.0f) pct = 0.0f;
  if (pct > 100.0f) pct = 100.0f;
  return pct;
}

static SensorSnapshot sampleSensors() {
  SensorSnapshot snapshot;
  snapshot.light = readLightRaw();
  snapshot.light_raw = static_cast<int>(analogRead(LIGHT_PIN));
  snapshot.distance = readDistanceCm();
  readEnvironment(snapshot.temperature, snapshot.humidity);
  snapshot.water_level = computeWaterLevelPercent(snapshot.distance);
  snapshot.water_raw = static_cast<int>(snapshot.water_level * 10.0f);
  last_snapshot = snapshot;
  return snapshot;
}

static String realtimePayload(const SensorSnapshot &snapshot) {
  String json = "{";
  json += "\"light\":" + String(snapshot.light, 1);
  json += ",\"distance\":" + String(snapshot.distance, 1);
  json += "}";
  return json;
}

static String hourlyPayload(const SensorSnapshot &snapshot) {
  String json = "{";
  json += "\"temperature\":" + String(snapshot.temperature, 1);
  json += ",\"humidity\":" + String(snapshot.humidity, 1);
  json += ",\"water_level\":" + String(snapshot.water_level, 1);
  json += ",\"water_raw\":" + String(snapshot.water_raw);
  json += ",\"light_raw\":" + String(snapshot.light_raw);
  json += "}";
  return json;
}

static bool postJson(const String &endpoint, const String &payload) {
  WiFiClient client;
  HTTPClient http;
  if (!http.begin(client, endpoint)) {
    Serial.printf("[http] begin failed: %s\n", endpoint.c_str());
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  const int code = http.POST(payload);
  const String response = http.getString();
  http.end();
  Serial.printf("[http] POST %s => %d %s\n", endpoint.c_str(), code, response.c_str());
  return code >= 200 && code < 300;
}

static void sendRealtime(const SensorSnapshot &snapshot) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[http] skipped because wifi is offline");
    return;
  }
  const String realtimeUrl = buildUrl("/sensor/realtime-ingest");
  const bool ok = postJson(realtimeUrl, realtimePayload(snapshot));
  Serial.printf(
      "[realtime] ok=%s light=%.1f distance=%.1f\n",
      ok ? "yes" : "no",
      snapshot.light,
      snapshot.distance);
}

static void sendHourly(const SensorSnapshot &snapshot) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[http] skipped because wifi is offline");
    return;
  }
  const String hourlyUrl = buildUrl("/sensor/hourly-ingest");
  const bool ok = postJson(hourlyUrl, hourlyPayload(snapshot));
  Serial.printf(
      "[hourly] ok=%s temp=%.1f hum=%.1f water=%.1f water_raw=%d light_raw=%d\n",
      ok ? "yes" : "no",
      snapshot.temperature,
      snapshot.humidity,
      snapshot.water_level,
      snapshot.water_raw,
      snapshot.light_raw);
}

static void sendSnapshot(const SensorSnapshot &snapshot, bool includeHourly) {
  sendRealtime(snapshot);
  if (includeHourly) {
    sendHourly(snapshot);
  }
}

void setup() {
  Serial.begin(115200);
  delay(250);
  Serial.println();
  Serial.println("[boot] Wemos sensor hub starting");
#if WEMOS_HAS_DHT
  dht.begin();
#endif
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  connectWiFi();
  last_tick_at = millis();
  last_hourly_at = millis();
  last_wifi_check_at = millis();
  last_wifi_log_at = millis();
}

void loop() {
  ensureWiFi();
  if (millis() - last_tick_at < SENSOR_INTERVAL_MS) {
    delay(25);
    return;
  }

  last_tick_at = millis();
  const SensorSnapshot snapshot = sampleSensors();
  bool includeHourly = (millis() - last_hourly_at >= 600000UL); // 10 minutes
  if (includeHourly) {
    last_hourly_at = millis();
  }
  sendSnapshot(snapshot, includeHourly);
}
