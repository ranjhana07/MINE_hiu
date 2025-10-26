import os
import time
import json
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
load_dotenv()

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', 8883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')


def on_connect(client, userdata, flags, rc):
    print('CONNECTED TO MQTT RC=', rc)
    client.subscribe('rfid')
    print('SUBSCRIBED to rfid')


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
    except Exception:
        payload = str(msg.payload)
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] MSG {msg.topic}: {payload}')


client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1, client_id=f"persistent-listener-{int(time.time())}")
client.on_connect = on_connect
client.on_message = on_message
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
client.tls_set_context(ctx)

print(f'CONNECTING to {MQTT_HOST}:{MQTT_PORT} ...')
client.connect(MQTT_HOST, MQTT_PORT, 60)

# loop_forever will block and print incoming messages to stdout
client.loop_start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('Stopping subscriber')
    client.loop_stop()
    client.disconnect()
