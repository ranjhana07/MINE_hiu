#!/usr/bin/env python3
"""
Publish RFID scans for TRISHALA (Node 93BA302D) at Station A1
This script publishes RFID messages to MQTT broker for testing checkpoint progression
"""
import os
import sys
import json
import time
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', '8883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_SECURE = os.getenv('MQTT_SECURE', 'true').lower() != 'false'

# TRISHALA configuration
STATION_ID = "A1"
TAG_ID = "93BA302D"
NAME = "TRISHALA"

client_id = f'trishala-rfid-pub-{os.getpid()}'
protocol = 'mqtts' if MQTT_SECURE else 'mqtt'

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# TLS
if MQTT_SECURE:
    import ssl
    context = ssl.create_default_context()
    # allow insecure for local testing if env requests it
    if os.getenv('MQTT_REJECT_UNAUTHORIZED', '').lower() == 'false':
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)

print(f'🔌 Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}')
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

print(f'\n{"="*60}')
print(f'📡 Publishing RFID scans for TRISHALA (93BA302D) at Station A1')
print(f'{"="*60}\n')

# Publish multiple scans to test forward and reverse checkpoint progression
num_scans = 8
for i in range(1, num_scans + 1):
    payload = {
        'station_id': STATION_ID,
        'tag_id': TAG_ID,
        'name': NAME
    }
    
    payload_json = json.dumps(payload)
    topic = 'rfid'
    
    print(f'Scan #{i}: Publishing to topic "{topic}"')
    print(f'  Payload: {payload_json}')
    
    res = client.publish(topic, payload_json, qos=1)
    res.wait_for_publish()
    
    print(f'  ✓ Published successfully')
    
    if i < num_scans:
        print(f'  ⏳ Waiting 4 seconds (debounce period)...\n')
        time.sleep(4)  # Wait 4 seconds to avoid debouncing (3 second window)

print(f'\n{"="*60}')
print(f'✅ All {num_scans} RFID scans published for TRISHALA!')
print(f'{"="*60}')

client.loop_stop()
client.disconnect()

print('\n📊 Check the dashboard to see checkpoint progression for NODE 93BA302D - TRISHALA')
print('   The checkpoints should progress forward then reverse in a cycle.')
