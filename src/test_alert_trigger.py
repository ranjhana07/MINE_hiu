#!/usr/bin/env python3
"""
Test script to simulate high heart rate data to trigger alerts in Mine Armour Dashboard
This will publish MQTT messages with heart rate > 10 to test the alert system
"""

import json
import time
import paho.mqtt.client as mqtt
import ssl
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # MQTT Configuration (same as dashboard)
    mqtt_host = os.getenv("MQTT_HOST")
    mqtt_port = int(os.getenv("MQTT_PORT", 8883))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    topic = "LOKI_2004"
    
    print(f"🧪 Testing Alert System - Publishing to {mqtt_host}:{mqtt_port}")
    print(f"📡 Topic: {topic}")
    
    # Create MQTT client
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    
    # Enable TLS
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)
    
    try:
        # Connect to MQTT broker
        print("🔌 Connecting to MQTT broker...")
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()
        time.sleep(2)  # Wait for connection
        
        # Test data with high heart rate to trigger alert
        test_data_samples = [
            {
                'heartRate': 15,  # Above threshold of 10
                'spo2': 98,
                'temperature': 36.5,
                'humidity': 45.0,
                'LPG': 5.2,
                'CH4': 4.8,
                'Propane': 3.9,
                'Butane': 4.1,
                'H2': 3.7,
                'GSR': 120,
                'stress': 1,
                'lat': 28.6139,
                'lon': 77.2090,
                'alt': 216.0,
                'sat': 8
            },
            {
                'heartRate': 22,  # Even higher to trigger another alert
                'spo2': 96,
                'temperature': 37.2,
                'humidity': 48.0,
                'LPG': 5.8,
                'CH4': 5.1,
                'Propane': 4.2,
                'Butane': 4.5,
                'H2': 4.0,
                'GSR': 145,
                'stress': 1,
                'lat': 28.6140,
                'lon': 77.2092,
                'alt': 218.0,
                'sat': 9
            },
            {
                'heartRate': 8,   # Below threshold - should not trigger alert
                'spo2': 99,
                'temperature': 36.8,
                'humidity': 44.0,
                'LPG': 4.9,
                'CH4': 4.5,
                'Propane': 3.6,
                'Butane': 3.8,
                'H2': 3.4,
                'GSR': 95,
                'stress': 0,
                'lat': 28.6141,
                'lon': 77.2094,
                'alt': 220.0,
                'sat': 10
            }
        ]
        
        print("\n🚨 Publishing test data to trigger alerts...")
        
        for i, data in enumerate(test_data_samples, 1):
            json_data = json.dumps(data)
            result = client.publish(topic, json_data)
            
            if data['heartRate'] > 10:
                print(f"📊 Sample {i}: Heart Rate = {data['heartRate']} BPM (SHOULD TRIGGER ALERT) ⚠️")
            else:
                print(f"📊 Sample {i}: Heart Rate = {data['heartRate']} BPM (Normal - no alert)")
            
            print(f"   Published: {json_data}")
            print(f"   Result: {result}")
            
            # Wait between samples
            time.sleep(3)
        
        print("\n✅ Test data published successfully!")
        print("🔍 Check the dashboard at http://localhost:8050 for alerts")
        print("📍 Go to: Zone selection → Select node → View vitals dashboard")
        print("🚨 Alerts should appear showing:")
        print("   - High heart rate: 15 BPM — Zone: [selected zone] Node: [selected node]")
        print("   - High heart rate: 22 BPM — Zone: [selected zone] Node: [selected node]")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        client.loop_stop()
        client.disconnect()
        print("🔌 Disconnected from MQTT broker")

if __name__ == "__main__":
    main()