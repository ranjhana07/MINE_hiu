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

# MQTT topics for sensor data
mqtt_topics = [
    os.getenv("MQTT_TOPIC_1", "LOKI_2004"),
    os.getenv("MQTT_TOPIC_2", "RANJ_2005"),
    os.getenv("MQTT_TOPIC_3", "TRISH_2005"),
    os.getenv("MQTT_TOPIC_4", "SUSH_2004/#"),
    os.getenv("MQTT_TOPIC_5", "SAM_2006")
]
# Filter out None values
mqtt_topics = [t for t in mqtt_topics if t]

if not all([host, port, mqtt_username, mqtt_password]):
    logging.error("Required MQTT environment variables not set")
    exit(1)

# Create MQTT client with TLS support (compatible with paho-mqtt v1.x and v2.x)
try:
    CallbackAPIVersion = getattr(mqtt, "CallbackAPIVersion", None)
    if CallbackAPIVersion is not None:
        # paho-mqtt v2.x
        client = mqtt.Client(client_id="SensorDataServer", protocol=mqtt.MQTTv311,
                             callback_api_version=CallbackAPIVersion.VERSION1)
    else:
        # paho-mqtt v1.x
        client = mqtt.Client(client_id="SensorDataServer", protocol=mqtt.MQTTv311)
except Exception as e:
    logging.warning(f"Falling back to default MQTT client creation: {e}")
    client = mqtt.Client()

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
        if topic in mqtt_topics or any(topic.startswith(t.rstrip('/#')) for t in mqtt_topics if '/#' in t):
            parse_gas_sensor_data(payload)
        else:
            logging.warning(f"Unknown topic received: {topic}")
            
    except Exception as e:
        logging.error(f"Error parsing data from topic {topic}: {e}")

def on_connect(client, userdata, flags, return_code):
    """MQTT connection callback"""
    if return_code == 0:
        logging.info("✅ Connected to MQTT broker")
        logging.info(f"📡 Subscribing to {len(mqtt_topics)} topics:")
        for topic in mqtt_topics:
            logging.info(f"   🔔 {topic}")
            client.subscribe(topic)
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
        logging.info(f"📡 Monitoring {len(mqtt_topics)} topics: {', '.join(mqtt_topics)}")
        
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
        # Start MQTT loop (use only one loop method; do not mix loop_start with loop_forever)

        # Helper to publish RFID scan events to topic 'rfid'
        def publish_rfid(station_id, tag_id, qos=1):
            try:
                topic = 'rfid'
                payload = json.dumps({
                    'station_id': station_id,
                    'tag_id': tag_id
                })
                logging.info(f"Publishing RFID -> topic={topic} payload={payload}")
                client.publish(topic, payload, qos=qos)
            except Exception as e:
                logging.error(f"Error publishing RFID message: {e}")

        # If environment requests a sample publish for testing, do it once
        if os.getenv('TEST_PUBLISH_SAMPLE_RFID') == '1':
            logging.info('TEST_PUBLISH_SAMPLE_RFID=1 set — publishing sample RFID message')
            publish_rfid('A1', 'TEST_TAG_001')
        # Keep original behavior (summary thread + running loop)
        client.loop_forever()
        
    except KeyboardInterrupt:
        logging.info("🛑 Shutting down gas sensor data server...")
        client.disconnect()
        logging.info("👋 Gas sensor data server stopped")
    except Exception as e:
        logging.error(f"❌ Error running gas sensor data server: {e}")

if __name__ == "__main__":
    run()