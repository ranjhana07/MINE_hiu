import json
import logging
import os
import ssl
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Environment variables
host = os.getenv("MQTT_HOST")
port = int(os.getenv("MQTT_PORT", "8883"))
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")

# MQTT topic for gas sensor data
mqtt_topic = "LOKI_2004"

if not all([host, port, mqtt_username, mqtt_password]):
    logging.error("Required MQTT environment variables not set")
    exit(1)

# Create MQTT client with TLS support
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "SensorDataServer")

# Configure TLS/SSL
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
client.tls_set_context(context)

# Set credentials
client.username_pw_set(mqtt_username, mqtt_password)

# Gas sensor data storage
gas_data = {
    "LPG": None,
    "CH4": None, 
    "Propane": None,
    "Butane": None,
    "H2": None,
    "timestamp": None
}

def parse_gas_sensor_data(payload):
    """Parse gas sensor data from LOKI_2004 topic"""
    try:
        # Parse JSON data like: {"LPG":125.14,"CH4":67.47,"Propane":94.18,"Butane":109.31,"H2":68.45}
        data = json.loads(payload)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update gas data
        gas_data["LPG"] = data.get("LPG")
        gas_data["CH4"] = data.get("CH4") 
        gas_data["Propane"] = data.get("Propane")
        gas_data["Butane"] = data.get("Butane")
        gas_data["H2"] = data.get("H2")
        gas_data["timestamp"] = timestamp
        
        # Log the gas readings
        logging.info(f"  GAS SENSOR [{timestamp[11:19]}]:")
        logging.info(f"   💨 LPG: {data.get('LPG', 'N/A')} ppm")
        logging.info(f"   🔥 CH4: {data.get('CH4', 'N/A')} ppm") 
        logging.info(f"   ⛽ Propane: {data.get('Propane', 'N/A')} ppm")
        logging.info(f"   🧪 Butane: {data.get('Butane', 'N/A')} ppm")
        logging.info(f"   💡 H2: {data.get('H2', 'N/A')} ppm")
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON gas sensor data '{payload}': {e}")
    except Exception as e:
        logging.error(f"Error processing gas sensor data '{payload}': {e}")

def parse_sensor_data(topic, payload):
    """Parse sensor data based on topic"""
    try:
        if topic == "LOKI_2004":
            parse_gas_sensor_data(payload)
        else:
            logging.warning(f"Unknown topic received: {topic}")
            
    except Exception as e:
        logging.error(f"Error parsing data from topic {topic}: {e}")

def on_connect(client, userdata, flags, return_code):
    """MQTT connection callback"""
    if return_code == 0:
        logging.info("✅ Connected to MQTT broker")
        logging.info(f"📡 Subscribing to topic: {mqtt_topic}")
        client.subscribe(mqtt_topic)
    else:
        logging.error(f"❌ Failed to connect to MQTT broker, return code: {return_code}")

def on_message(client, userdata, message):
    """MQTT message callback"""
    try:
        topic = message.topic
        payload = message.payload.decode('utf-8')
        logging.info(f"📨 Raw message on {topic}: {payload}")
        parse_sensor_data(topic, payload)
    except Exception as e:
        logging.error(f"Error processing message on topic {topic}: {e}")

def print_gas_summary():
    """Print a summary of gas sensor data every 30 seconds"""
    while True:
        time.sleep(30)
        logging.info("📊 === GAS SENSOR SUMMARY ===")
        
        if gas_data["timestamp"]:
            logging.info(f"   📈 Last Update: {gas_data['timestamp']}")
            logging.info(f"   💨 LPG: {gas_data['LPG']} ppm")
            logging.info(f"     CH4: {gas_data['CH4']} ppm")
            logging.info(f"   ⛽ Propane: {gas_data['Propane']} ppm") 
            logging.info(f"   🧪 Butane: {gas_data['Butane']} ppm")
            logging.info(f"     H2: {gas_data['H2']} ppm")
        else:
            logging.info("   📉 No gas sensor data received yet")
        
        logging.info("==================================================")

# Set event handlers
client.on_connect = on_connect
client.on_message = on_message

def run():
    """Main function to run the gas sensor data server"""
    try:
        logging.info("🛡 MINE ARMOUR - GAS SENSOR DATA SERVER")
        logging.info("==================================================")
        logging.info(f"🔗 Connecting to MQTT broker: {host}:{port}")
        logging.info(f"📡 Monitoring topic: {mqtt_topic}")
        
        # Connect to MQTT broker
        client.connect(host, port, 60)
        
        # Start gas summary thread
        import threading
        summary_thread = threading.Thread(target=print_gas_summary, daemon=True)
        summary_thread.start()
        
        logging.info("✅ Gas sensor data server started successfully!")
        logging.info("📊 Real-time gas monitoring active")
        logging.info("🔄 Data ready for dashboard display")
        logging.info("🛑 Press Ctrl+C to stop monitoring")
        
        # Start MQTT loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        logging.info("🛑 Shutting down gas sensor data server...")
        client.disconnect()
        logging.info("👋 Gas sensor data server stopped")
    except Exception as e:
        logging.error(f"❌ Error running gas sensor data server: {e}")

if __name__ == "__main__":
    run()