#!/usr/bin/env python3
"""Simple test publisher to send RFID scan messages to the MQTT broker.

Usage:
  python test_publish_rfid.py --station A1 --tag TAG123

Reads MQTT credentials from environment (.env) and publishes to topic 'rfid'.
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', '8883'))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_SECURE = os.getenv('MQTT_SECURE', 'true').lower() != 'false'

parser = argparse.ArgumentParser()
parser.add_argument('--station', '-s', required=True, help='Station id (e.g. A1)')
parser.add_argument('--tag', '-t', required=True, help='Tag id (e.g. TAG123)')
parser.add_argument('--qos', type=int, default=1)
args = parser.parse_args()

client_id = f'test-rfid-pub-{os.getpid()}'
protocol = 'mqtts' if MQTT_SECURE else 'mqtt'
url = f'{protocol}://{MQTT_HOST}:{MQTT_PORT}'

options = {
    'client_id': client_id,
    'reconnect_on_failure': False,
}

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

print(f'Connecting to {MQTT_HOST}:{MQTT_PORT} as {MQTT_USERNAME or "<none>"}...')
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

payload = json.dumps({'station_id': args.station, 'tag_id': args.tag})
topic = 'rfid'
print(f'Publishing {payload} to {topic}')
res = client.publish(topic, payload, qos=args.qos)
res.wait_for_publish()
print('Published, exiting')
client.loop_stop()
client.disconnect()
