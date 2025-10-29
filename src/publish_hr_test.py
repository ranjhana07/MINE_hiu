#!/usr/bin/env python3
"""
Publish a few test heart rate messages to MQTT to exercise dashboard alerts.
Uses the same .env configuration as the dashboard (TLS on 8883, MQTT v3.1.1).
"""
import json
import ssl
import time
import os
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("MQTT_HOST")
PORT = int(os.getenv("MQTT_PORT", "8883"))
USER = os.getenv("MQTT_USERNAME")
PASS = os.getenv("MQTT_PASSWORD")
TOPIC = os.getenv("MQTT_TOPIC_1", "LOKI_2004")

# Small helper to build a secure client compatible with paho v1/v2
CallbackAPIVersion = getattr(mqtt, 'CallbackAPIVersion', None)
if CallbackAPIVersion is not None:
    client = mqtt.Client(client_id=f"MineArmourTestPub-{int(time.time())}", protocol=mqtt.MQTTv311, callback_api_version=CallbackAPIVersion.VERSION1)
else:
    client = mqtt.Client(client_id=f"MineArmourTestPub-{int(time.time())}", protocol=mqtt.MQTTv311)

if USER and PASS:
    client.username_pw_set(USER, PASS)

# TLS (trust-any for easy testing, mirrors dashboard setup)
ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
client.tls_set_context(ctx)

print(f"Connecting to {HOST}:{PORT} and publishing to topic '{TOPIC}'...")
client.connect(HOST, PORT, 60)
client.loop_start()

# Build three messages: low HR, high HR, normal HR
msgs = [
    {"heartRate": 15, "spo2": 98, "name": "Test User", "station_id": "A1", "timestamp": datetime.utcnow().isoformat()},
    {"heartRate": 105, "spo2": 97, "name": "Test User", "station_id": "A1", "timestamp": datetime.utcnow().isoformat()},
    {"heartRate": 65, "spo2": 98, "name": "Test User", "station_id": "A1", "timestamp": datetime.utcnow().isoformat()},
]

for i, payload in enumerate(msgs, 1):
    s = json.dumps(payload)
    rc = client.publish(TOPIC, s, qos=1)
    print(f"[{i}/3] Published: {s}")
    time.sleep(1.0)

client.loop_stop()
client.disconnect()
print("Done.")
