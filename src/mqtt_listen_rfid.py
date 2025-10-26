import os
from dotenv import load_dotenv
load_dotenv()
import time
import json
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', 8883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')

received = []

def on_connect(client, userdata, flags, rc):
    print('sub connected rc', rc)
    client.subscribe('rfid')
    print('subscribed to rfid')

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
    except Exception:
        payload = str(msg.payload)
    print('MSG', msg.topic, payload)
    received.append((msg.topic, payload))

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1, client_id=f"rfid-listener-{int(time.time())}")
client.on_connect = on_connect
client.on_message = on_message
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
client.tls_set_context(ctx)

client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

print('Listening for 12s...')
time.sleep(12)
client.loop_stop()
print('Done. Received:', received)
