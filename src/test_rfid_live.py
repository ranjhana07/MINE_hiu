#!/usr/bin/env python3
"""
Quick RFID Test Script
Publishes test RFID scans to check dashboard response
"""

import paho.mqtt.client as mqtt
import json
import time
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

# MQTT Config
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

def publish_rfid_scan(client, station_id, tag_id):
    """Publish an RFID scan"""
    payload = {
        "station_id": station_id,
        "tag_id": tag_id
    }
    
    # Try multiple topics
    topics = ["rfid", "rfid/scan", "LOKI_2004"]
    
    for topic in topics:
        client.publish(topic, json.dumps(payload))
        print(f"✓ Published to {topic}: {payload}")
    
    time.sleep(0.5)

def main():
    print("\n" + "="*60)
    print("RFID TEST PUBLISHER")
    print("="*60)
    
    # Setup MQTT client
    try:
        CallbackAPIVersion = getattr(mqtt, 'CallbackAPIVersion', None)
        if CallbackAPIVersion:
            client = mqtt.Client(client_id='RFIDTester', protocol=mqtt.MQTTv311, 
                               callback_api_version=CallbackAPIVersion.VERSION1)
        else:
            client = mqtt.Client(client_id='RFIDTester', protocol=mqtt.MQTTv311)
        
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)
        
        print(f"\nConnecting to {MQTT_HOST}:{MQTT_PORT}...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(2)
        
        print("\n📡 Publishing test scans for Tag C7761005...")
        print("-" * 60)
        
        # Publish 4 sequential scans
        scans = [
            ("A1", "C7761005", "Main Gate Checkpoint"),
            ("A2", "C7761005", "Weighbridge Checkpoint"),
            ("A3", "C7761005", "Fuel Station Checkpoint"),
            ("A4", "C7761005", "Workshop Checkpoint")
        ]
        
        for i, (station, tag, checkpoint) in enumerate(scans, 1):
            print(f"\nScan {i}/4: {checkpoint}")
            publish_rfid_scan(client, station, tag)
            time.sleep(4)  # Wait 4 seconds between scans (longer than debounce)
        
        print("\n" + "="*60)
        print("✅ TEST COMPLETE - Check dashboard for updates!")
        print("="*60 + "\n")
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")

if __name__ == "__main__":
    main()
