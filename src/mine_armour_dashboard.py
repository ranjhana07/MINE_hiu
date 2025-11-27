#!/usr/bin/env python3
"""
Mine Armour - Real-time Multi-Sensor Dashboard
Displays real-time sensor data from MQTT broker
Sensors: Gas (LPG, CH4, Propane, Butane, H2), Heart Rate, Temperature, Humidity, GSR, GPS
"""

import os
import sys
import json
import time
import threading
import ssl
from datetime import datetime, timedelta
from collections import deque
import logging

# Third-party imports
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context
from flask import request, jsonify
import dash_bootstrap_components as dbc
import dash
from dash.exceptions import PreventUpdate

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SensorDataManager:
    """Manages real-time multi-sensor data storage and retrieval"""
    















































































































































































































































































































































































































































































































































































    def __init__(self, max_points=100):
        self.max_points = max_points
        self.data = {
            'gas_sensors': {
                'timestamps': deque(maxlen=max_points),
                'LPG': deque(maxlen=max_points),
                'CH4': deque(maxlen=max_points),
                'Propane': deque(maxlen=max_points),
                'Butane': deque(maxlen=max_points),
                'H2': deque(maxlen=max_points),
                'latest': {
                    'LPG': 0,
                    'CH4': 0,
                    'Propane': 0,
                    'Butane': 0,
                    'H2': 0,
                    'timestamp': None
                }
            },
            'health_sensors': {
                'timestamps': deque(maxlen=max_points),
                'heartRate': deque(maxlen=max_points),
                'spo2': deque(maxlen=max_points),
                'GSR': deque(maxlen=max_points),
                'stress': deque(maxlen=max_points),
            },
            'environmental_sensors': {
                'timestamps': deque(maxlen=max_points),
                'temperature': deque(maxlen=max_points),
                'humidity': deque(maxlen=max_points),
            },
            'gps_data': {
                'timestamps': deque(maxlen=max_points),
                'lat': deque(maxlen=max_points),
                'lon': deque(maxlen=max_points),
                'alt': deque(maxlen=max_points),
                'sat': deque(maxlen=max_points),
                'latest': {
                    'lat': 0.0,
                    'lon': 0.0,
                    'alt': 0.0,
                    'sat': 0
                }
            },
            'rfid_checkpoints': {
                'timestamps': deque(maxlen=max_points),
                'uid_scans': deque(maxlen=max_points),
                'latest_tag': None,
                'latest_station': None,
                'checkpoint_progress': {},  # Maps node_id -> {checkpoint_id: passed_timestamp}
                'active_checkpoints': {
                    # Zone A checkpoints
                    '1298': ['Entry Gate', 'Safety Check', 'Equipment Bay', 'Deep Section'],
                    '1753': ['Main Tunnel', 'Gas Monitor', 'Emergency Exit'],
                    '1456': ['Shaft Entry', 'Mining Face', 'Ventilation Hub'],
                    # Primary node set used across all zones (project uses these 4 nodes)
                    # Zone A checkpoint names (standardised across the primary nodes)
                    'C7761005': ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint'],
                    '93BA302D': ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint'],
                    '7AA81505': ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint'],
                    'DB970104': ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint'],
                    # Zone B and C checkpoint lists removed; only four primary node IDs are used for all zones
                }
            }
        }
        self.lock = threading.Lock()
        # Per-tag scan counters to support sequence-based checkpoint progression
        # Keyed by lower-case tag id. Used for special-case flows (e.g. c7761005 in Zone A)
        self._rfid_tag_scan_counts = {}
        # Track last scan time for each tag to prevent duplicate rapid scans
        self._last_scan_time = {}  # Format: {(tag_id, station_id): timestamp}
        # Track last checkpoint index seen per tag (to detect wrap-around)
        self._rfid_tag_last_index = {}
        # Track last detected direction per tag ('forward' or 'reverse')
        self._rfid_tag_direction = {}
    
    def add_gas_data(self, data):
        """Add new sensor data point"""
        with self.lock:
            timestamp = datetime.now()
            
            # Add gas sensor data
            self.data['gas_sensors']['timestamps'].append(timestamp)
            
            lpg = data.get('LPG', 0)
            ch4 = data.get('CH4', 0)
            propane = data.get('Propane', 0)
            butane = data.get('Butane', 0)
            h2 = data.get('H2', 0)
            
            self.data['gas_sensors']['LPG'].append(lpg)
            self.data['gas_sensors']['CH4'].append(ch4)
            self.data['gas_sensors']['Propane'].append(propane)
            self.data['gas_sensors']['Butane'].append(butane)
            self.data['gas_sensors']['H2'].append(h2)
            
            # Add health sensor data
            self.data['health_sensors']['timestamps'].append(timestamp)
            heartRate = data.get('heartRate', -1)
            spo2 = data.get('spo2', -1)
            gsr = data.get('GSR', 0)
            stress = data.get('stress', 0)
            
            self.data['health_sensors']['heartRate'].append(heartRate if heartRate != -1 else None)
            self.data['health_sensors']['spo2'].append(spo2 if spo2 != -1 else None)
            self.data['health_sensors']['GSR'].append(gsr)
            self.data['health_sensors']['stress'].append(stress)
            
            # Add environmental sensor data
            self.data['environmental_sensors']['timestamps'].append(timestamp)
            temperature = data.get('temperature', -1.0)
            humidity = data.get('humidity', -1.0)
            
            self.data['environmental_sensors']['temperature'].append(temperature if temperature != -1.0 else None)
            self.data['environmental_sensors']['humidity'].append(humidity if humidity != -1.0 else None)
            
            # Add GPS data
            self.data['gps_data']['timestamps'].append(timestamp)
            lat = data.get('lat', 0.0)
            lon = data.get('lon', 0.0)
            alt = data.get('alt', 0.0)
            sat = data.get('sat', 0)
            
            self.data['gps_data']['lat'].append(lat)
            self.data['gps_data']['lon'].append(lon)
            self.data['gps_data']['alt'].append(alt)
            self.data['gps_data']['sat'].append(sat)
            
            # Optional identity/zone metadata if present on the message
            person_name = data.get('name') or data.get('person') or data.get('user')
            station_id_msg = data.get('station_id')
            zone_from_msg = data.get('zone')
            # Derive a simple zone label from station id when available (e.g. A1 -> Zone A)
            derived_zone = None
            try:
                if isinstance(station_id_msg, str) and station_id_msg:
                    derived_zone = f"Zone {station_id_msg[0].upper()}"
            except Exception:
                derived_zone = None

            zone_label = zone_from_msg or derived_zone

            # Update latest values with ALL sensor data
            self.data['gas_sensors']['latest'] = {
                'LPG': lpg,
                'CH4': ch4,
                'Propane': propane,
                'Butane': butane,
                'H2': h2,
                'heartRate': heartRate,
                'spo2': spo2,
                'temperature': temperature,
                'humidity': humidity,
                'GSR': gsr,
                'stress': stress,
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'sat': sat,
                'name': person_name,
                'zone': zone_label,
                'timestamp': timestamp
            }
            
            # Update GPS latest
            self.data['gps_data']['latest'] = {
                'lat': lat,
                'lon': lon,
                'alt': alt,
                'sat': sat
            }
            
            logging.info(f"All sensor data updated: Gas={lpg:.2f}, GPS=({lat:.6f},{lon:.6f}), Health=HR:{heartRate},SpO2:{spo2}")
    
    def get_gas_data(self):
        """Get gas sensor data for plotting"""
        with self.lock:
            return self.data['gas_sensors'].copy()
    
    def get_health_data(self):
        """Get health sensor data for plotting"""
        with self.lock:
            return self.data['health_sensors'].copy()
    
    def get_environmental_data(self):
        """Get environmental sensor data for plotting"""
        with self.lock:
            return self.data['environmental_sensors'].copy()
    
    def get_gps_data(self):
        """Get GPS data for mapping"""
        with self.lock:
            return self.data['gps_data'].copy()
    
    def add_rfid_data(self, rfid_data):
        """Add new RFID checkpoint data"""
        with self.lock:
            timestamp = datetime.now()
            
            # Extract data from new RFID format: {"station_id": "A1", "tag_id": "TAG123"}
            station_id = rfid_data.get('station_id', '')
            tag_id = rfid_data.get('tag_id', '')
            
            # DEBOUNCING: Ignore duplicate scans within 3 seconds
            scan_key = (tag_id, station_id)
            if scan_key in self._last_scan_time:
                time_since_last = (timestamp - self._last_scan_time[scan_key]).total_seconds()
                if time_since_last < 3.0:  # 3 second debounce window
                    logging.info(f"RFID scan ignored (debounce): {tag_id} at {station_id} (last scan {time_since_last:.1f}s ago)")
                    return
            
            # Update last scan time
            self._last_scan_time[scan_key] = timestamp
            
            # Map station_id to node_id and checkpoint (you can customize this mapping)
            # Station format examples: A1, A2, B1, B2, etc.
            zone = station_id[0] if station_id else ''  # Extract zone letter (A, B, C)
            station_num = station_id[1:] if len(station_id) > 1 else '1'  # Extract station number
            
            # Map zones to node IDs
            # Use the 4 primary nodes for every zone (A/B/C) so station numbers map to these nodes
            zone_nodes = {
                'A': ['C7761005', '93BA302D', '7AA81505', 'DB970104'],
                'B': ['C7761005', '93BA302D', '7AA81505', 'DB970104'],
                'C': ['C7761005', '93BA302D', '7AA81505', 'DB970104']
            }
            
            # Get node_id based on zone and station number
            if zone in zone_nodes:
                nodes = zone_nodes[zone]
                node_idx = (int(station_num) - 1) % len(nodes)
                node_id = nodes[node_idx]
            else:
                node_id = station_id  # Fallback to station_id if no mapping
            
            # Map station to checkpoint names
            checkpoint_mapping = {
                # Map station IDs to the checkpoint names used in active_checkpoints
                # so that progress keys match the UI's expected checkpoint list.
                'A1': 'Main Gate Checkpoint',
                'A2': 'Weighbridge Checkpoint',
                'A3': 'Fuel Station Checkpoint',
                'A4': 'Workshop Checkpoint',
                'B1': 'North Entry',
                'B2': 'Equipment Room',
                'B3': 'Gas Detection', 
                'B4': 'Exit Portal',
                'C1': 'South Gate',
                'C2': 'Tool Center',
                'C3': 'Deep Shaft',
                'C4': 'Return Path'
            }
            # Default checkpoint id from mapping
            checkpoint_id = checkpoint_mapping.get(station_id, f'Station {station_id}')

            # Whether we've already handled marking/unmarking for this special-case
            skip_auto_mark = False

            # Special-case: for tag C7761005 and 93BA302D (case-insensitive), advance the
            # checkpoint progress sequentially on every unique scan. Each scan
            # advances to the next configured checkpoint for that node (cycles).
            try:
                tag_lc = tag_id.lower() if isinstance(tag_id, str) else ''
            except Exception:
                tag_lc = ''

            if tag_lc in ['c7761005', '93ba302d']:
                # Determine the target node ID based on tag
                target_node = 'C7761005' if tag_lc == 'c7761005' else '93BA302D'
                
                # Increment the per-tag counter (absolute count) for each unique scan
                cnt = self._rfid_tag_scan_counts.get(tag_lc, 0) + 1
                self._rfid_tag_scan_counts[tag_lc] = cnt

                # Get ordered checkpoint list for this node
                node_checkpoints = self.data['rfid_checkpoints']['active_checkpoints'].get(
                    target_node,
                    ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint']
                )
                n = len(node_checkpoints)

                # Compute position in a forward-then-reverse cycle of length 2*n
                pos = ((cnt - 1) % (2 * n)) + 1

                # Helper to mark/unmark
                def _mark(node, idx_mark):
                    chk = node_checkpoints[idx_mark]
                    if node not in self.data['rfid_checkpoints']['checkpoint_progress']:
                        self.data['rfid_checkpoints']['checkpoint_progress'][node] = {}
                    self.data['rfid_checkpoints']['checkpoint_progress'][node][chk] = timestamp

                def _unmark_idx(node, idx_un):
                    chk = node_checkpoints[idx_un]
                    try:
                        if node in self.data['rfid_checkpoints']['checkpoint_progress'] and chk in self.data['rfid_checkpoints']['checkpoint_progress'][node]:
                            del self.data['rfid_checkpoints']['checkpoint_progress'][node][chk]
                    except Exception:
                        logging.exception("Error unmarking checkpoint")

                if pos <= n:
                    # Forward pass: mark checkpoint at index pos-1
                    idx = pos - 1
                    _mark(target_node, idx)
                    checkpoint_id = node_checkpoints[idx]
                else:
                    # Reverse pass: pos in [n+1 .. 2n] -> unmark index = 2n - pos
                    idx_un = (2 * n) - pos
                    _unmark_idx(target_node, idx_un)
                    checkpoint_id = node_checkpoints[idx_un]

                # Force the node to the target node so progress is stored under that person's node
                node_id = target_node

                # Special-case: we handled marking/unmarking manually; prevent the
                # generic automatic mark below from overriding it.
                skip_auto_mark = True
            
            # Store the scan
            self.data['rfid_checkpoints']['timestamps'].append(timestamp)
            self.data['rfid_checkpoints']['uid_scans'].append({
                'tag_id': tag_id,
                'station_id': station_id,
                'node_id': node_id,
                'checkpoint': checkpoint_id,
                'timestamp': timestamp
            })
            
            self.data['rfid_checkpoints']['latest_tag'] = tag_id
            self.data['rfid_checkpoints']['latest_station'] = station_id
            # Store latest seen name if provided by publisher (used for alert context)
            if 'name' in rfid_data:
                self.data['rfid_checkpoints']['latest_name'] = rfid_data.get('name')
            
            # Update checkpoint progress for specific nodes (skip if special-case handled it)
            if not skip_auto_mark:
                if node_id and checkpoint_id:
                    if node_id not in self.data['rfid_checkpoints']['checkpoint_progress']:
                        self.data['rfid_checkpoints']['checkpoint_progress'][node_id] = {}
                    self.data['rfid_checkpoints']['checkpoint_progress'][node_id][checkpoint_id] = timestamp
            
            logging.info(f"RFID checkpoint updated: Station={station_id}, Tag={tag_id}, Node={node_id}, Checkpoint={checkpoint_id}")
    
    def reset_checkpoint_progress(self, node_id=None, tag_id=None):
        """Reset checkpoint progress for a specific node or tag"""
        with self.lock:
            if tag_id:
                # Reset tag scan counter
                tag_lc = tag_id.lower() if isinstance(tag_id, str) else ''
                if tag_lc in self._rfid_tag_scan_counts:
                    del self._rfid_tag_scan_counts[tag_lc]
                    logging.info(f"Reset scan counter for tag {tag_id}")
            
            if node_id:
                # Reset checkpoint progress for node
                if node_id in self.data['rfid_checkpoints']['checkpoint_progress']:
                    del self.data['rfid_checkpoints']['checkpoint_progress'][node_id]
                    logging.info(f"Reset checkpoint progress for node {node_id}")
            
            if not node_id and not tag_id:
                # Reset everything
                self._rfid_tag_scan_counts.clear()
                self.data['rfid_checkpoints']['checkpoint_progress'].clear()
                logging.info("Reset all checkpoint progress")
    
    def get_rfid_data(self):
        """Get RFID checkpoint data"""
        with self.lock:
            return self.data['rfid_checkpoints'].copy()
    
    def get_checkpoint_status(self, node_id):
        """Get checkpoint status for a specific node"""
        with self.lock:
            checkpoints = self.data['rfid_checkpoints']['active_checkpoints'].get(node_id, [])
            progress = self.data['rfid_checkpoints']['checkpoint_progress'].get(node_id, {})
            
            # Return list of (checkpoint_name, is_passed, timestamp)
            status = []
            for checkpoint in checkpoints:
                is_passed = checkpoint in progress
                timestamp = progress.get(checkpoint) if is_passed else None
                status.append((checkpoint, is_passed, timestamp))
            
            return status

class MQTTClient:
    """MQTT client for receiving gas sensor data"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.client = None
        self.connected = False
        
        # MQTT Configuration from environment
        self.mqtt_host = os.getenv("MQTT_HOST")
        self.mqtt_port = int(os.getenv("MQTT_PORT", 8883))
        self.mqtt_username = os.getenv("MQTT_USERNAME")
        self.mqtt_password = os.getenv("MQTT_PASSWORD")
        
        # MQTT Topics (from env with default)
        self.gas_topic = os.getenv("MQTT_TOPIC_1", "LOKI_2004")
        self.rfid_topic = "rfid"  # RFID checkpoint topic (subscription disabled by request)
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info("Connected to MQTT broker")
            # Subscribe to gas sensor topic (primary source)
            client.subscribe(self.gas_topic)
            logging.info(f"Subscribed to {self.gas_topic}")
            # Subscribe to RFID topics to receive checkpoint scans
            client.subscribe("rfid")
            client.subscribe("rfid/#")
            logging.info("Subscribed to RFID topics: rfid and rfid/#")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")
    
    def on_message(self, client, userdata, message):
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')

            # Attempt to parse JSON payload
            data = None
            try:
                data = json.loads(payload)
            except Exception:
                logging.debug(f"Non-JSON payload on {topic}: {payload}")

            # If this message was published on the dedicated RFID topic, route to RFID handler
            if topic == self.rfid_topic:
                if isinstance(data, dict):
                    self.data_manager.add_rfid_data(data)
                    logging.info(f"Received RFID data on {self.rfid_topic}: {data}")
                else:
                    logging.warning(f"Received non-dict RFID payload on {self.rfid_topic}: {payload}")

            # If message was published on the gas topic, try to detect whether it actually
            # contains RFID scan fields (some publishers send scans to LOKI_2004). If so,
            # route to the RFID handler; otherwise treat it as gas sensor data.
            elif topic == self.gas_topic:
                if isinstance(data, dict) and 'tag_id' in data and 'station_id' in data:
                    # Treat as RFID scan published to gas topic
                    self.data_manager.add_rfid_data(data)
                    logging.info(f"Detected RFID scan on {self.gas_topic}, processed as RFID: {data}")
                elif isinstance(data, dict):
                    # Regular gas sensor payload
                    self.data_manager.add_gas_data(data)
                    logging.info(f"Received gas data: {data}")
                else:
                    logging.warning(f"Received unexpected payload on {self.gas_topic}: {payload}")
            else:
                # For any other topics, attempt to intelligently route if possible
                if isinstance(data, dict) and 'tag_id' in data and 'station_id' in data:
                    self.data_manager.add_rfid_data(data)
                    logging.info(f"Received RFID-style payload on {topic}, processed as RFID: {data}")
                elif isinstance(data, dict):
                    # Unknown dict payload; send to gas handler by default
                    self.data_manager.add_gas_data(data)
                    logging.info(f"Received dict payload on {topic}, processed as gas-data fallback: {data}")
                else:
                    logging.debug(f"Unhandled message on {topic}: {payload}")

        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.info("Disconnected from MQTT broker")
    
    def connect(self):
        try:
            # Create MQTT client compatible with paho v1.x and v2.x, force MQTT 3.1.1
            CallbackAPIVersion = getattr(mqtt, 'CallbackAPIVersion', None)
            if CallbackAPIVersion is not None:
                # paho-mqtt v2.x path
                self.client = mqtt.Client(
                    client_id='MineArmourDash',
                    protocol=mqtt.MQTTv311,
                    callback_api_version=CallbackAPIVersion.VERSION1
                )
            else:
                # paho-mqtt v1.x path
                self.client = mqtt.Client(client_id='MineArmourDash', protocol=mqtt.MQTTv311)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            if self.mqtt_username and self.mqtt_password:
                self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Enable TLS for secure connection  
            import ssl
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)
            
            self.client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.client.loop_start()
            
            logging.info(f"Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            
        except Exception as e:
            logging.error(f"Error connecting to MQTT: {e}")
    
    def disconnect(self):
        """Properly disconnect from MQTT broker"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logging.info("MQTT client disconnected properly")
            except Exception as e:
                logging.error(f"Error disconnecting MQTT: {e}")

# Initialize data manager and MQTT client
data_manager = SensorDataManager()
mqtt_client = MQTTClient(data_manager)

# Initialize Dash app with modern dark theme
app = dash.Dash(__name__, external_stylesheets=[
    dbc.themes.CYBORG,  # Dark theme
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"  # Icons
])
app.title = "🛡 Mine Armour - Gas Sensor Dashboard"
app.config.suppress_callback_exceptions = True

# --- Lightweight helper HTTP endpoints for testing/resetting RFID counters
# These run on the same Flask server that Dash uses and are intended for
# development/testing only. They let you simulate RFID payloads or reset
# per-tag scan counters without restarting the dashboard.
@app.server.route('/simulate_rfid', methods=['POST'])
def simulate_rfid():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return ("Invalid JSON", 400)

    if not isinstance(payload, dict):
        return ("Expected JSON object", 400)

    # Allow direct simulation of RFID scan into data_manager
    try:
        data_manager.add_rfid_data(payload)
        return ("OK", 200)
    except Exception as e:
        logging.error(f"Error in simulate_rfid: {e}")
        return ("Internal Error", 500)


@app.server.route('/reset_rfid_counter', methods=['POST'])
def reset_rfid_counter():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return ("Invalid JSON", 400)

    tag = payload.get('tag_id') if isinstance(payload, dict) else None
    if not tag:
        return ("Missing tag_id", 400)

    tag_lc = tag.lower()
    try:
        # Remove the tag counter so sequence restarts
        if tag_lc in data_manager._rfid_tag_scan_counts:
            data_manager._rfid_tag_scan_counts.pop(tag_lc, None)
            return (f"Counter reset for {tag}", 200)
        else:
            return (f"No counter present for {tag}", 200)
    except Exception as e:
        logging.error(f"Error resetting RFID counter: {e}")
        return ("Internal Error", 500)


@app.server.route('/rfid_counters', methods=['GET'])
def rfid_counters():
    try:
        return jsonify(data_manager._rfid_tag_scan_counts)
    except Exception as e:
        logging.error(f"Error returning rfid counters: {e}")
        return ("Internal Error", 500)

# Simple helper endpoint to simulate heart-rate messages for testing alerts
# Example: GET /simulate_hr?hr=105&name=Test%20User&station=A1
@app.server.route('/simulate_hr', methods=['GET'])
def simulate_hr():
    try:
        hr_str = request.args.get('hr')
        if hr_str is None:
            return ("Missing hr query parameter", 400)
        try:
            hr = float(hr_str)
        except ValueError:
            return ("Invalid hr value", 400)

        name = request.args.get('name') or 'Test User'
        station = request.args.get('station') or 'A1'

        payload = {
            'heartRate': hr,
            'spo2': 98,
            'name': name,
            'station_id': station,
            'temperature': 26.7,
            'humidity': 68.0,
            'LPG': 0,
            'CH4': 0,
            'Propane': 0,
            'Butane': 0,
            'H2': 0,
            'GSR': 0,
            'stress': 0,
            'lat': 0.0,
            'lon': 0.0,
            'alt': 0.0,
            'sat': 0,
        }
        data_manager.add_gas_data(payload)
        return ("OK", 200)
    except Exception as e:
        logging.error(f"Error in simulate_hr: {e}")
        return ("Internal Error", 500)

# Custom CSS styling with darker red-black gradient theme
custom_style = {
    'backgroundColor': '#000000',
    'background': 'linear-gradient(135deg, #000000 0%, #4B0000 50%, #000000 100%)',
    'color': '#ffffff',
    'minHeight': '100vh'
}

# Header styling with darker red-black gradient
header_style = {
    'background': 'linear-gradient(135deg, #4B0000 0%, #800000 50%, #2D0000 100%)',
    'padding': '20px',
    'borderRadius': '10px',
    'marginBottom': '30px',
    'boxShadow': '0 4px 15px rgba(128, 0, 0, 0.6)',
    'border': '2px solid #800000'
}

# Card styling with darker red theme
card_style = {
    'backgroundColor': '#1A0000',
    'border': '2px solid #4B0000',
    'borderRadius': '10px',
    'boxShadow': '0 2px 10px rgba(75, 0, 0, 0.5)',
    'background': 'linear-gradient(135deg, #1A0000 0%, #2D0000 100%)'
}

# Chart styling with darker red theme
chart_style = {
    'backgroundColor': '#1A0000',
    'background': 'linear-gradient(135deg, #0D0000 0%, #1A0000 100%)',
    'borderRadius': '10px',
    'padding': '10px',
    'boxShadow': '0 2px 10px rgba(75, 0, 0, 0.5)',
    'border': '1px solid #4B0000'
}

## Removed experimental DEMO_ZONES, ENABLE_DEMO_SIMULATION, and ZoneDemoState (rollback).

# Custom CSS for darker red-black gradient background
app.index_string = '''
<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background: linear-gradient(135deg, #000000 0%, #4B0000 25%, #800000 50%, #4B0000 75%, #000000 100%) !important;
                background-attachment: fixed !important;
                margin: 0;
                padding: 0;
            }
            .dash-bootstrap {
                background: transparent !important;
            }
            /* Landing page card styles */
            .landing-wrapper {display:flex;align-items:center;justify-content:center;min-height:100vh;padding:40px;}
            .landing-card {max-width:480px;width:100%;background:linear-gradient(145deg,#1A0000 0%,#2D0000 55%,#1A0000 100%);border:1px solid #800000;box-shadow:0 10px 35px rgba(128,0,0,0.55),0 4px 12px rgba(0,0,0,0.6);padding:55px 50px 50px;border-radius:22px;position:relative;overflow:hidden;}
            .landing-card:before {content:"";position:absolute;inset:0;background:radial-gradient(circle at 30% 20%,rgba(255,80,80,0.25),transparent 60%),radial-gradient(circle at 80% 70%,rgba(255,0,0,0.18),transparent 65%);pointer-events:none;}
            .landing-title {font-weight:800;font-size:3rem;text-align:center;margin:0 0 2.2rem;color:#ffffff;letter-spacing:1px;text-shadow:0 0 18px rgba(255,60,60,0.55),0 0 6px rgba(255,255,255,0.3);}            
            .landing-dropdown .Select-control {background:#140000;border:1px solid #990000;color:#fff;box-shadow:0 0 0 2px rgba(255,0,0,0.15);}            
            .landing-dropdown .Select-placeholder, .landing-dropdown .Select-value-label {color:#ffdede !important;font-weight:600;letter-spacing:.5px;}
            .landing-dropdown .Select-menu-outer {background:#220000;border:1px solid #990000;}
            .landing-dropdown .Select-option {background:#220000;color:#ffffff;font-size:0.85rem;}
            .landing-dropdown .Select-option.is-focused {background:#551111;}
            .landing-dropdown .Select-option.is-selected {background:#770000;}
            .landing-btn {display:block;width:100%;margin-top:2.2rem;padding:14px 30px;font-weight:700;letter-spacing:1px;font-size:0.95rem;background:linear-gradient(90deg,#c60000,#ff2626);border:none;border-radius:10px;color:#fff;box-shadow:0 6px 16px rgba(255,0,0,0.4),0 2px 4px rgba(0,0,0,0.5);transition:all .25s ease;}
            .landing-btn:hover {transform:translateY(-3px);box-shadow:0 10px 24px rgba(255,0,0,0.55),0 4px 10px rgba(0,0,0,0.55);}
            .landing-btn:active {transform:translateY(0);}
            .landing-subtext {text-align:center;margin-top:1rem;font-size:0.75rem;letter-spacing:.5px;color:#ffb3b3;opacity:.8;}
            @media (max-width:600px){.landing-card{padding:50px 28px 45px;border-radius:18px;} .landing-title{font-size:2.4rem;margin-bottom:2rem;} }
            /* Removed experimental zone/worker CSS */
            /* Zone dropdown styling */
            #zone-dropdown .Select-control {background:#1A0000; border:1px solid #4B0000; color:#ffffff;}
            #zone-dropdown .Select-placeholder, 
            #zone-dropdown .Select-value-label {color:#ffffff !important; font-weight:600; letter-spacing:.5px;}
            #zone-dropdown .Select-menu-outer {background:#2D0000; border:1px solid #4B0000;}
            #zone-dropdown .Select-option {background:#2D0000; color:#ffffff; font-size:0.8rem;}
            #zone-dropdown .Select-option.is-focused {background:#550000;}
            #zone-dropdown .Select-option.is-selected {background:#800000;}
            #zone-dropdown .Select-arrow {border-top-color:#ffffff !important;}
            #zone-dropdown .Select-control:hover {box-shadow:0 0 6px #ff4444;}
            .node-context-banner {background:linear-gradient(90deg,#2D0000,#4B0000);border:1px solid #800000;border-radius:8px;padding:6px 14px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,0.4);}            
            .node-pill {background:#800000;border:1px solid #ffaaaa;color:#fff;font-size:0.75rem;font-weight:600;letter-spacing:.5px;padding:4px 10px;border-radius:16px;box-shadow:0 0 6px #ff4444;}            
            .zone-pill {background:#2D0000;border:1px solid #aa4444;color:#ffdddd;font-size:0.7rem;font-weight:600;padding:4px 10px;border-radius:14px;}            
            .metric-value {font-size:1.9rem; line-height:1.1; font-weight:700; letter-spacing:.5px;}
            @media (max-width:1400px){ .metric-value {font-size:1.6rem;} }
            @media (max-width:1200px){ .metric-value {font-size:1.4rem;} }
            /* RFID Checkpoint Animation */
            @keyframes pulse {
                0% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.5); }
                50% { box-shadow: 0 0 25px rgba(0, 255, 136, 0.8), 0 0 35px rgba(0, 255, 136, 0.3); }
                100% { box-shadow: 0 0 15px rgba(0, 255, 136, 0.5); }
            }
            /* New blinking highlight for first Main Tunnel checkpoint */
            @keyframes blink {
                0% { transform: scale(1); box-shadow: 0 0 8px 2px rgba(255,255,0,0.35); }
                50% { transform: scale(1.10); box-shadow: 0 0 16px 4px rgba(255,255,0,0.95); }
                100% { transform: scale(1); box-shadow: 0 0 8px 2px rgba(255,255,0,0.35); }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Dashboard layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='chosen-zone-store'),
    dcc.Store(id='alerts-store'),
    dcc.Store(id='last-hr-store'),
    dcc.Store(id='selected-node-store', storage_type='session'),
    dcc.Store(id='checkpoint-reset-store', storage_type='session'),
    dcc.Store(id='auth-store', storage_type='session'),
    # Global interval so alerts monitoring runs even on the landing page
    # Reduced to 3000ms (3 seconds) to prevent UI "freaking out" from too many updates
    dcc.Interval(id='global-interval', interval=3000, n_intervals=0),
    html.Div(id='page-content')
])

# ---------------------------
# Page: Zone Selection
# ---------------------------
def zone_select_layout():
    # Side-by-side layout: Zone selection on LEFT, Alerts on RIGHT - both boxes equal
    return html.Div([
        # Container with two equal boxes side by side
        html.Div([
            # Left Box - MINE ARMOUR Zone Selection
            html.Div([
                html.H1("MINE ARMOUR", style={
                    'color': '#ffffff',
                    'fontSize': '2.5rem',
                    'fontWeight': '800',
                    'textAlign': 'center',
                    'marginBottom': '8px',
                    'letterSpacing': '1px',
                    'textShadow': '0 0 18px rgba(255,60,60,0.55)'
                }),
                html.Div("Protecting Miners Preserving Lives", style={
                    'fontSize': '0.85rem',
                    'textAlign': 'center',
                    'marginBottom': '25px',
                    'letterSpacing': '.8px',
                    'color': '#ffcccc',
                    'fontWeight': '600'
                }),
                # 2x2 Grid of Zone Cards
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardBody([
                            html.H3("Zone A", style={'color':'#fff','fontWeight':'700','marginBottom':'10px','textAlign':'center'}),
                            dbc.Button("ENTER Zone A", id='zone-A-btn', color='danger', n_clicks=0, style={'width':'100%','fontWeight':'600'})
                        ])
                    ], style=card_style), width=6),
                    dbc.Col(dbc.Card([
                        dbc.CardBody([
                            html.H3("Zone B", style={'color':'#fff','fontWeight':'700','marginBottom':'10px','textAlign':'center'}),
                            dbc.Button("ENTER Zone B", id='zone-B-btn', color='danger', n_clicks=0, style={'width':'100%','fontWeight':'600'})
                        ])
                    ], style=card_style), width=6)
                ], className='mb-3'),
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardBody([
                            html.H3("Zone C", style={'color':'#fff','fontWeight':'700','marginBottom':'10px','textAlign':'center'}),
                            dbc.Button("ENTER Zone C", id='zone-C-btn', color='danger', n_clicks=0, style={'width':'100%','fontWeight':'600'})
                        ])
                    ], style=card_style), width=6),
                    dbc.Col(dbc.Card([
                        dbc.CardBody([
                            html.H3("Zone D", style={'color':'#fff','fontWeight':'700','marginBottom':'10px','textAlign':'center'}),
                            dbc.Button("ENTER Zone D", id='zone-D-btn', color='danger', n_clicks=0, style={'width':'100%','fontWeight':'600'})
                        ])
                    ], style=card_style), width=6)
                ]),
                html.Div(id='zone-select-msg', style={'textAlign':'center','marginTop':'15px','color':'#ffb3b3','fontSize':'0.75rem'})
            ], style={
                'background': 'linear-gradient(145deg, #1A0000 0%, #2D0000 55%, #1A0000 100%)',
                'border': '2px solid #800000',
                'borderRadius': '20px',
                'padding': '40px 30px',
                'boxShadow': '0 10px 35px rgba(128,0,0,0.55), 0 4px 12px rgba(0,0,0,0.6)',
                'width': '550px',
                'height': '580px'
            }),

            # Right Box - Live Alerts (EXACT same size as left box)
            html.Div([
                html.H1("Live Alerts", style={
                    'color': '#ffffff',
                    'fontSize': '2.5rem',
                    'fontWeight': '800',
                    'textAlign': 'center',
                    'marginBottom': '8px',
                    'letterSpacing': '1px',
                    'textShadow': '0 0 18px rgba(255,60,60,0.55)'
                }),
                html.Div("Real-time Safety Monitoring", style={
                    'fontSize': '0.85rem',
                    'textAlign': 'center',
                    'marginBottom': '25px',
                    'letterSpacing': '.8px',
                    'color': '#ffcccc',
                    'fontWeight': '600'
                }),
                html.Div(id='landing-alerts-list', children=[
                    html.P("No active alerts", style={'color': '#99aab5', 'textAlign': 'center', 'fontStyle': 'italic', 'marginTop': '80px', 'fontSize': '1.1rem'})
                ], style={
                    'minHeight': '320px',
                    'maxHeight': '320px',
                    'overflowY': 'auto',
                    'paddingRight': '10px',
                    'marginBottom': '18px',
                    'flex': '1'
                }),
                dbc.Button("Clear All Alerts", id='landing-clear-alerts-btn', color='danger', size='lg', 
                          style={'width': '100%', 'fontWeight': '700', 'letterSpacing': '1px', 'padding': '12px'})
            ], style={
                'background': 'linear-gradient(145deg, #1A0000 0%, #2D0000 55%, #1A0000 100%)',
                'border': '2px solid #800000',
                'borderRadius': '20px',
                'padding': '40px 30px',
                'boxShadow': '0 10px 35px rgba(128,0,0,0.55), 0 4px 12px rgba(0,0,0,0.6)',
                'width': '550px',
                'height': '580px',
                'display': 'flex',
                'flexDirection': 'column'
            })

        ], style={
            'display': 'flex',
            'gap': '40px',
            'alignItems': 'center',
            'justifyContent': 'center',
            'minHeight': '100vh',
            'padding': '40px'
        })
    ])

# ---------------------------
# Page: Nodes Selection 
# ---------------------------
def nodes_layout(zone_name):
    # Get nodes for the selected zone
    # Use the same primary 4 named nodes across all zones so Zone B/C/D show the
    # same node cards as Zone A (matches the RFID/node mapping used elsewhere).
    primary_nodes = [
        {'id': 'C7761005', 'name': 'NODE C7761005 - SUSHMA', 'status': 'Active'},
        {'id': '93BA302D', 'name': 'NODE 93BA302D - TRISHALA', 'status': 'Active'},
        {'id': '7AA81505', 'name': 'NODE 7AA81505 - RANJHANA', 'status': 'Active'},
        {'id': 'DB970104', 'name': 'NODE DB970104 - LOKESH', 'status': 'Active'}
    ]

    zone_nodes = {
        'ZONE_A': primary_nodes,
        'ZONE_B': primary_nodes,
        'ZONE_C': primary_nodes,
        'ZONE_D': primary_nodes
    }
    
    nodes = zone_nodes.get(zone_name, [])
    
    # Create node cards
    node_cards = []
    for node in nodes:
        card = dbc.Card([
            dbc.CardBody([
                html.H4(node['name'], className='card-title', style={'color': '#ff4444', 'marginBottom': '8px'}),
                html.P(f"Node ID: {node['id']}", style={'color': '#cccccc', 'marginBottom': '4px'}),
                html.P(f"Status: {node['status']}", style={'color': '#00ff88', 'marginBottom': '12px'}),
                html.Button(
                    "SELECT NODE",
                    id={'type': 'node-select-btn', 'index': node['id']},
                    n_clicks=0,
                    className='btn btn-danger',
                    style={
                        'background': 'linear-gradient(45deg, #cc0000, #ff4444)',
                        'border': 'none',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'width': '100%',
                        'padding': '8px'
                    }
                )
            ])
        ], style={
            'background': 'linear-gradient(135deg, #1a0000, #330000)',
            'border': '1px solid #660000',
            'marginBottom': '15px',
            'boxShadow': '0 4px 8px rgba(255,68,68,0.2)'
        })
        node_cards.append(card)
    
    return html.Div([
        html.Div([
            html.Div([
                html.H1("MINE ARMOUR", className='landing-title'),
                html.Div(f"Select Node in {zone_name.replace('_', ' ')}", 
                        className='landing-subtext', 
                        style={'fontSize':'0.95rem','marginTop':'-18px','marginBottom':'20px','letterSpacing':'.8px','color':'#ffcccc','fontWeight':'600'}),
                
                html.Div(node_cards, style={'maxHeight': '400px', 'overflowY': 'auto', 'padding': '10px'}),
                
                html.Div([
                    html.Button("← BACK TO ZONES", 
                               id='back-to-zones-btn', 
                               n_clicks=0, 
                               className='landing-btn',
                               style={'marginTop': '15px', 'background': 'linear-gradient(45deg, #666666, #999999)'})
                ], style={'textAlign': 'center'})
                
            ], className='landing-card', style={'maxWidth': '600px'})
        ], className='landing-wrapper')
    ])

# ---------------------------
# Login Page (hard-coded demo creds)
# ---------------------------
def login_layout():
    return html.Div([
        html.Div([
            html.Div([
                html.H1("MINE ARMOUR", className='landing-title'),
                html.Div("Protecting Miners, Preserving Lives", className='landing-subtext', style={'marginTop':'-18px','fontSize':'0.9rem'}),
                dbc.Input(id='login-username', placeholder='Username', type='text', value='', style={'marginBottom':'14px','background':'#140000','color':'#fff','border':'1px solid #990000'}),
                dbc.Input(id='login-password', placeholder='Password', type='password', value='', style={'marginBottom':'8px','background':'#140000','color':'#fff','border':'1px solid #990000'}),
                html.Button('LOGIN', id='login-btn', n_clicks=0, className='landing-btn'),
                html.Div(id='login-msg', className='landing-subtext', style={'marginTop':'12px'}),
                html.Div(html.Small('Demo: admin / admin123', style={'opacity':0.5}), style={'textAlign':'center','marginTop':'4px'})
            ], className='landing-card', style={'maxWidth':'520px'})
        ], className='landing-wrapper')
    ])

# ---------------------------
# Page: Vitals Dashboard (existing content refactored)
# ---------------------------
def vitals_layout():
    return dbc.Container([
    # Header Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
                    html.I(className="fas fa-hard-hat me-3", style={
                        'color': '#FFFFFF', 
                        'fontSize': '3rem',
                        'textShadow': '3px 3px 6px rgba(0,0,0,0.8)',
                        'filter': 'drop-shadow(0 0 20px #800000)',
                        'transform': 'rotate(-5deg)'
                    }),
                    "MINE ARMOUR"
                ], className="text-center mb-4", 
                   style={'color': '#ffffff', 'font-weight': 'bold', 'fontSize': '3rem'}),
                html.P([
                    html.I(className="fas fa-broadcast-tower me-2"),
                    "MQTT Topic: " + os.getenv("MQTT_TOPIC_1", "LOKI_2004") + " | ",
                    html.I(className="fas fa-clock me-2"),
                    "Live Updates Every Second | ",
                    html.I(className="fas fa-microchip me-2"),
                    "Multi-Sensor Monitoring"
                ], className="text-center mb-0",
                   style={'color': '#a5b4fc', 'fontSize': '1.1rem'})
            ], style=header_style)
        ])
    ], className="mb-4"),
    
    # Connection Status Bar
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.I(className="fas fa-wifi me-2"),
                html.Span(id="connection-status", style={'fontWeight': 'bold'})
            ], id="status-alert", color="success", className="mb-0")
        ])
    ], className="mb-4"),

    # Current Zone/Node Display (read-only)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.Span("Zone A", className='zone-pill', style={'marginRight':'8px'}),
                    html.Small("Live monitoring dashboard", style={'color':'#ffcccc','opacity':0.8}),
                    dbc.Button("Change Zone", color="outline-light", size="sm", href="/", style={'marginLeft':'auto','fontSize':'0.75rem'})
                ], style={'display':'flex','alignItems':'center','justifyContent':'space-between'})
            ], className='node-context-banner')
        ], width=12)
    ], className='mb-3'),
    
    # Current Values Grid
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-fire text-danger", style={'fontSize': '2rem'}),
               html.H3(id="lpg-current", className="metric-value mb-0 mt-2", style={'color': '#ff6b6b'}),
                        html.P("LPG Gas Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-cloud text-primary", style={'fontSize': '2rem'}),
               html.H3(id="ch4-current", className="metric-value mb-0 mt-2", style={'color': '#4ecdc4'}),
                        html.P("CH4 (Methane)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-gas-pump text-success", style={'fontSize': '2rem'}),
               html.H3(id="propane-current", className="metric-value mb-0 mt-2", style={'color': '#45b7d1'}),
                        html.P("Propane Gas", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-burn text-warning", style={'fontSize': '2rem'}),
               html.H3(id="butane-current", className="metric-value mb-0 mt-2", style={'color': '#f39c12'}),
                        html.P("Butane Gas", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-atom text-info", style={'fontSize': '2rem'}),
               html.H3(id="h2-current", className="metric-value mb-0 mt-2", style={'color': '#9b59b6'}),
                        html.P("H2 (Hydrogen)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-chart-line text-success", style={'fontSize': '2rem'}),
                        html.H6("System Status", className="mb-2 mt-2", style={'color': '#ffffff'}),
                        html.P(id="last-update", className="text-muted mb-0", style={'fontSize': '0.9rem'})
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2)
    ], className="mb-4"),
    
    # Additional Sensor Values Grid
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-heartbeat text-danger", style={'fontSize': '2rem'}),
               html.H3(id="heartrate-current", className="metric-value mb-0 mt-2", style={'color': '#e74c3c'}),
                        html.P("Heart Rate (BPM)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-lungs text-info", style={'fontSize': '2rem'}),
               html.H3(id="spo2-current", className="metric-value mb-0 mt-2", style={'color': '#3498db'}),
                        html.P("SpO2 (%)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-thermometer-half text-warning", style={'fontSize': '2rem'}),
               html.H3(id="temperature-current", className="metric-value mb-0 mt-2", style={'color': '#f39c12'}),
                        html.P("Temperature (°C)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-tint text-primary", style={'fontSize': '2rem'}),
               html.H3(id="humidity-current", className="metric-value mb-0 mt-2", style={'color': '#2980b9'}),
                        html.P("Humidity (%)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-hand-paper text-success", style={'fontSize': '2rem'}),
               html.H3(id="gsr-current", className="metric-value mb-0 mt-2", style={'color': '#27ae60'}),
                        html.P("GSR Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-brain text-danger", style={'fontSize': '2rem'}),
               html.H3(id="stress-current", className="metric-value mb-0 mt-2", style={'color': '#e67e22'}),
                        html.P("Stress Level", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=2)
    ], className="mb-4"),
    
    # RFID Checkpoint Status Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H4([
                        "RFID Checkpoint Status"
                    ], style={'color': '#ffffff', 'margin': '0'})
                ], style={'background': 'linear-gradient(45deg, #660000, #990000)', 'border': 'none'}),
                dbc.CardBody([
                    html.Div([
                        html.Div([
                            html.P("Selected Node:", style={'color': '#cccccc', 'marginBottom': '5px', 'fontSize': '0.9rem'}),
                            html.H5(id="selected-node-display", children="No node selected", 
                                   style={'color': '#ffffff', 'marginBottom': '15px'})
                        ]),
                        html.Div([
                            html.P("Latest RFID Scan:", style={'color': '#cccccc', 'marginBottom': '5px', 'fontSize': '0.9rem'}),
                            html.H6(id="latest-rfid-scan", children="No scans yet", 
                                   style={'color': '#ffcccc', 'marginBottom': '15px'})
                        ]),
                        html.Hr(style={'borderColor': '#660000', 'margin': '15px 0'}),
                        html.Div([
                            html.H6("Checkpoint Flow Diagram:", style={'color': '#ffffff', 'marginBottom': '15px', 'textAlign': 'center'}),
                            html.Div(id="checkpoint-flow-diagram", children=[
                                html.P("Select a node to view checkpoint flow", 
                                      style={'color': '#999999', 'fontStyle': 'italic', 'textAlign': 'center'})
                            ], style={
                                'minHeight': '120px',
                                'display': 'flex',
                                'alignItems': 'center',
                                'justifyContent': 'center',
                                'background': 'linear-gradient(135deg, #0d0000, #1a0000)',
                                'border': '1px solid #440000',
                                'borderRadius': '8px',
                                'padding': '15px'
                            })
                        ])
                    ])
                ], style={'background': 'linear-gradient(135deg, #1a0000, #330000)', 'color': '#ffffff'})
            ], style={'border': '1px solid #660000', 'boxShadow': '0 4px 8px rgba(255,107,107,0.2)'})
        ], width=12)
    ], className="mb-4"),

    # Alerts Section (shows important alerts like high heart rate with zone/node context)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.H4([
                        "Alerts"
                    ], style={'color': '#ffffff', 'margin': '0'})
                ], style={'background': 'linear-gradient(45deg, #2d0000, #550000)', 'border': 'none'}),
                dbc.CardBody([
                    html.Div(id='alerts-list', children=[
                        html.P("No alerts", style={'color': '#99aab5'})
                    ]),
                    html.Div([
                        dbc.Button("Clear Alerts", id='clear-alerts-btn', color='danger', size='sm')
                    ], style={'textAlign': 'right', 'marginTop': '10px'})
                ], style={'background': 'linear-gradient(135deg, #1a0000, #330000)', 'color': '#ffffff'})
            ], style={'border': '1px solid #660000', 'boxShadow': '0 4px 8px rgba(255,107,107,0.2)'}),
        ], width=12)
    ], className='mb-4'),
    
    # GPS and Additional Sensors Section Header
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-satellite-dish me-3"),
                "🛰 REAL-TIME GPS TRACKING & SENSOR MONITORING"
            ], className="text-center mb-4", 
               style={'color': '#ffffff', 'fontWeight': 'bold'})
        ])
    ], className="mb-4"),
    
    # GPS Information Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-crosshairs text-danger", style={'fontSize': '2rem'}),
                        html.H4(id="gps-lat", className="mb-0 mt-2", 
                               style={'color': '#e74c3c', 'fontWeight': 'bold'}),
                        html.P("Latitude", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-compass text-primary", style={'fontSize': '2rem'}),
                        html.H4(id="gps-lon", className="mb-0 mt-2", 
                               style={'color': '#3498db', 'fontWeight': 'bold'}),
                        html.P("Longitude", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-mountain text-success", style={'fontSize': '2rem'}),
                        html.H4(id="gps-alt", className="mb-0 mt-2", 
                               style={'color': '#27ae60', 'fontWeight': 'bold'}),
                        html.P("Altitude (m)", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-satellite text-warning", style={'fontSize': '2rem'}),
                        html.H4(id="gps-sat", className="mb-0 mt-2", 
                               style={'color': '#f39c12', 'fontWeight': 'bold'}),
                        html.P("Satellites", className="text-muted mb-0")
                    ], className="text-center")
                ])
            ], style=card_style)
        ], width=3)
    ], className="mb-4"),
    
    # Enhanced GPS Map (Full Width) and Health Sensor Chart
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="gps-map", 
                         config={
                             'displayModeBar': True,
                             'displaylogo': False,
                             'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                             'modeBarButtonsToAdd': ['resetViews']
                         },
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=8),  # Larger GPS map
        dbc.Col([
            html.Div([
                dcc.Graph(id="heartrate-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=4)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="spo2-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="temperature-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="humidity-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="gsr-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    # Charts Section Header
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-chart-area me-3"),
                "Real-time Gas Sensor Charts"
            ], className="text-center mb-4", 
               style={'color': '#ffffff', 'fontWeight': 'bold'})
        ])
    ], className="mb-4"),
    
    # Gas Sensor Charts with enhanced styling
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="lpg-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="ch4-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="propane-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6),
        dbc.Col([
            html.Div([
                dcc.Graph(id="butane-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=6)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="h2-chart", 
                         config={'displayModeBar': False},
                         style={'backgroundColor': 'transparent'})
            ], style=chart_style)
        ], width=12)
    ], className="mb-4"),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=2000,  # Update every 2 seconds (reduced from 1s to prevent UI overload)
        n_intervals=0
    ),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(style={'borderColor': '#636e72'}),
            html.P([
                html.I(className="fas fa-hard-hat me-2"),
                "Mine Armour Dashboard | ",
                html.I(className="fas fa-calendar me-2"),
                "2025 | ",
                html.I(className="fas fa-code me-2"),
                "Real-time Gas Monitoring System"
            ], className="text-center text-muted mb-3",
               style={'fontSize': '0.9rem'})
        ])
    ])
    
], fluid=True, style=custom_style)

def serve_layout():
    return app.layout

@app.callback(
    Output('page-content','children'),
    Input('url','pathname'),
    State('chosen-zone-store','data'),
    State('auth-store','data')
)
def display_page(pathname, zone_data, auth_data):
    # Allow zone selection and node browsing without login.
    # Only require login for the protected '/vitals' page.
    # Expose the login page explicitly at '/login'.
    if pathname == '/login':
        return login_layout()
    # If user is not authenticated and they hit the root page, redirect to /login
    if not auth_data and pathname == '/':
        return dcc.Location(pathname='/login', id='redirect-to-login')

    if not auth_data and pathname == '/vitals':
        return login_layout()
    if pathname == '/nodes':
        # Show nodes page for the selected zone
        if zone_data and 'zone' in zone_data:
            return nodes_layout(zone_data['zone'])
        else:
            # No zone selected, go back to zone selection
            return zone_select_layout()
    if pathname == '/vitals':
        return vitals_layout()
    # default root -> zone selection
    return zone_select_layout()

@app.callback(
    [Output('chosen-zone-store','data'), Output('zone-select-msg','children'), Output('url','pathname', allow_duplicate=True)],
    [Input('zone-A-btn','n_clicks'), Input('zone-B-btn','n_clicks'), Input('zone-C-btn','n_clicks'), Input('zone-D-btn','n_clicks')],
    prevent_initial_call=True
)
def go_to_nodes(n_a, n_b, n_c, n_d):
    """Handle clicks on the zone cards and navigate to the nodes page for the selected zone."""
    # Determine which button triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    triggered = ctx.triggered[0]['prop_id'].split('.')[0]

    # Map the zone-card button id to a zone value
    mapping = {
        'zone-A-btn': 'ZONE_A',
        'zone-B-btn': 'ZONE_B',
        'zone-C-btn': 'ZONE_C',
        'zone-D-btn': 'ZONE_D'
    }
    zone = mapping.get(triggered, None)
    if not zone:
        raise PreventUpdate
    return {'zone': zone}, '', '/nodes'


# (zone card clicks are handled in the merged go_to_nodes callback above)

# ---------------------------
# Login callback
# ---------------------------
@app.callback(
    [Output('auth-store','data'), Output('login-msg','children'), Output('url','pathname', allow_duplicate=True)],
    Input('login-btn','n_clicks'),
    State('login-username','value'),
    State('login-password','value'),
    prevent_initial_call=True
)
def login_action(n, username, password):
    if not username or not password:
        return dash.no_update, 'Enter username and password.', dash.no_update
    if username == 'admin' and password == 'admin123':
        return {'user':'admin'}, 'Login success. Redirecting...', '/'
    return dash.no_update, 'Invalid credentials.', dash.no_update

## Removed zone/worker demo callbacks and synthetic worker chart filters.

# Callbacks for real-time updates
@app.callback(
    [
        Output('connection-status', 'children'),
        Output('lpg-current', 'children'),
        Output('ch4-current', 'children'),
        Output('propane-current', 'children'),
        Output('butane-current', 'children'),
        Output('h2-current', 'children'),
        Output('last-update', 'children'),
        Output('heartrate-current', 'children'),
        Output('spo2-current', 'children'),
        Output('temperature-current', 'children'),
        Output('humidity-current', 'children'),
        Output('gsr-current', 'children'),
        Output('stress-current', 'children'),
        Output('gps-lat', 'children'),
        Output('gps-lon', 'children'),
        Output('gps-alt', 'children'),
        Output('gps-sat', 'children'),
    ],
    Input('interval-component', 'n_intervals')
)
def update_current_values(n):
    try:
        from datetime import datetime
        
        # Connection status
        status = "Connected" if mqtt_client.connected else "Disconnected"
        
        # Get latest gas sensor values
        gas_data = data_manager.get_gas_data()
        gps_data = data_manager.get_gps_data()
        
        # Format gas sensor values with better error handling
        latest = gas_data.get('latest', {})
        lpg_val = f"{latest.get('LPG', 0):.2f}" if latest.get('LPG') is not None else "---"
        ch4_val = f"{latest.get('CH4', 0):.2f}" if latest.get('CH4') is not None else "---"
        propane_val = f"{latest.get('Propane', 0):.2f}" if latest.get('Propane') is not None else "---"
        butane_val = f"{latest.get('Butane', 0):.2f}" if latest.get('Butane') is not None else "---"
        h2_val = f"{latest.get('H2', 0):.2f}" if latest.get('H2') is not None else "---"
        
        # Format additional sensor values
        heart_val = f"{latest.get('heartRate', -1)}" if latest.get('heartRate', -1) != -1 else "---"
        spo2_val = f"{latest.get('spo2', -1):.1f}%" if latest.get('spo2', -1) != -1 else "---"
        temp_val = f"{latest.get('temperature', -1.0):.1f}°C" if latest.get('temperature', -1.0) != -1.0 else "---"
        hum_val = f"{latest.get('humidity', -1.0):.1f}%" if latest.get('humidity', -1.0) != -1.0 else "---"
        gsr_val = f"{latest.get('GSR', 0)}" if latest.get('GSR', 0) else "---"
        stress_val = "HIGH" if latest.get('stress', 0) == 1 else "LOW"
        
        # Format GPS values
        gps_latest = gps_data.get('latest', {})
        lat_val = f"{gps_latest.get('lat', 0.0):.6f}" if gps_latest.get('lat', 0.0) else "---"
        lon_val = f"{gps_latest.get('lon', 0.0):.6f}" if gps_latest.get('lon', 0.0) else "---"
        alt_val = f"{gps_latest.get('alt', 0.0):.1f}" if gps_latest.get('alt', 0.0) else "---"
        sat_val = f"{gps_latest.get('sat', 0)}" if gps_latest.get('sat', 0) else "0"
        
        # Last update timestamp
        now = datetime.now()
        last_update = now.strftime("%H:%M:%S")
        
        return [status, lpg_val, ch4_val, propane_val, butane_val, h2_val, f"Last: {last_update}",
                heart_val, spo2_val, temp_val, hum_val, gsr_val, stress_val,
                lat_val, lon_val, alt_val, sat_val]
                
    except Exception as e:
        # Return default values if there's an error
        now = datetime.now()
        last_update = now.strftime("%H:%M:%S")
        return ["Disconnected", "---", "---", "---", "---", "---", f"Error: {last_update}",
                "---", "---", "---", "---", "---", "LOW",
                "---", "---", "---", "0"]

@app.callback(
    Output('lpg-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_lpg_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['LPG']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['LPG']),
            mode='lines+markers',
            name='LPG',
            line=dict(color='#800000', width=3),
            marker=dict(size=6, color='#800000'),
            fill='tonexty',
            fillcolor='rgba(128, 0, 0, 0.2)'
        ))
    
    fig.update_layout(
        title={
            'text': "🔥 LPG Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#FFFFFF', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="LPG Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,0,0,0.3)',
        font={'color': '#FFFFFF'},
        xaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        ),
        yaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        )
    )
    return fig

@app.callback(
    Output('ch4-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_ch4_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['CH4']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['CH4']),
            mode='lines+markers',
            name='CH4',
            line=dict(color='#4B0000', width=3),
            marker=dict(size=6, color='#4B0000'),
            fill='tonexty',
            fillcolor='rgba(75, 0, 0, 0.2)'
        ))
    
    fig.update_layout(
        title={
            'text': "💨 CH4 (Methane) Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#FFFFFF', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="CH4 Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,0,0,0.3)',
        font={'color': '#FFFFFF'},
        xaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        ),
        yaxis=dict(
            gridcolor='#4B0000',
            tickfont={'color': '#FFFFFF'}
        )
    )
    return fig

@app.callback(
    Output('propane-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_propane_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['Propane']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['Propane']),
            mode='lines+markers',
            name='Propane',
            line=dict(color='#45b7d1', width=3),
            marker=dict(size=6, color='#45b7d1'),
            fill='tonexty',
            fillcolor='rgba(69, 183, 209, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "⛽ Propane Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Propane Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('butane-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_butane_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['Butane']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['Butane']),
            mode='lines+markers',
            name='Butane',
            line=dict(color='#f39c12', width=3),
            marker=dict(size=6, color='#f39c12'),
            fill='tonexty',
            fillcolor='rgba(243, 156, 18, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "🧨 Butane Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Butane Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('h2-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_h2_chart(n):
    gas_data = data_manager.get_gas_data()
    
    fig = go.Figure()
    if gas_data['timestamps'] and gas_data['H2']:
        fig.add_trace(go.Scatter(
            x=list(gas_data['timestamps']),
            y=list(gas_data['H2']),
            mode='lines+markers',
            name='H2',
            line=dict(color='#9b59b6', width=3),
            marker=dict(size=6, color='#9b59b6'),
            fill='tonexty',
            fillcolor='rgba(155, 89, 182, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "⚡ H2 (Hydrogen) Gas Sensor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="H2 Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

# GPS Map Callback
@app.callback(
    Output('gps-map', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_gps_map(n):
    """Render GPS map with trail and current location. Clean version (corruption removed)."""
    try:
        gps_data = data_manager.get_gps_data()
        fig = go.Figure()
        latest = gps_data.get('latest', {})
        current_lat = latest.get('lat', 0.0)
        current_lon = latest.get('lon', 0.0)
        current_alt = latest.get('alt', 0.0)
        current_sat = latest.get('sat', 0)

        # Valid coordinate check (avoid 0,0)
        if current_lat and current_lon and (current_lat != 0.0 or current_lon != 0.0):
            lat_history = list(gps_data.get('lat', []))
            lon_history = list(gps_data.get('lon', []))
            timestamps = list(gps_data.get('timestamps', []))

            # Trail (last up to 25 points excluding current)
            if len(lat_history) > 2 and len(lon_history) > 2:
                trail_lat = lat_history[-26:-1]
                trail_lon = lon_history[-26:-1]
                if trail_lat and trail_lon:
                    fig.add_trace(go.Scattermapbox(
                        lat=trail_lat,
                        lon=trail_lon,
                        mode='lines+markers',
                        marker=dict(size=6, color='#007BFF', opacity=0.6),
                        line=dict(width=2, color='#007BFF'),
                        name='GPS Trail',
                        hovertemplate='<b>Trail</b><br>Lat %{lat:.6f}<br>Lon %{lon:.6f}<extra></extra>'
                    ))

            # Current location marker
            fig.add_trace(go.Scattermapbox(
                lat=[current_lat],
                lon=[current_lon],
                mode='markers',
                marker=dict(size=28, color='#FF0000', symbol='circle'),
                name='Current Location',
                text=f"Lat: {current_lat:.6f}<br>Lon: {current_lon:.6f}<br>Alt: {current_alt:.1f}m<br>Sats: {current_sat}",
                hovertemplate='<b>Current</b><br>%{text}<extra></extra>'
            ))

            fig.update_layout(
                mapbox=dict(style='open-street-map', center=dict(lat=current_lat, lon=current_lon), zoom=16),
                title={'text': f"GPS Tracking | {current_lat:.6f}, {current_lon:.6f} | Alt {current_alt:.1f}m | Sats {current_sat}", 'x':0.5, 'font':{'color':'#ffffff','size':14}},
                height=450,
                margin=dict(l=0,r=0,t=40,b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color':'#ffffff'},
                showlegend=False
            )
        else:
            # No data yet
            fig.update_layout(
                title={'text': '🌍 GPS Location - Waiting for Signal...', 'x':0.5, 'font':{'color':'#ffffff','size':16}},
                height=450,
                margin=dict(l=0,r=0,t=40,b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                font={'color':'#ffffff'},
                annotations=[dict(
                    text='📡 Searching for GPS signal...<br>Please wait for location data',
                    showarrow=False, xref='paper', yref='paper', x=0.5, y=0.5,
                    xanchor='center', yanchor='middle',
                    font=dict(size=16, color='white'),
                    bgcolor='rgba(0,0,0,0.7)', bordercolor='white', borderwidth=1
                )]
            )
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(
            title={'text':'⚠ GPS Map Error','x':0.5,'font':{'color':'#FF6B6B','size':16}},
            height=450,
            margin=dict(l=0,r=0,t=40,b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color':'#ffffff'},
            annotations=[dict(
                text=f'Error loading GPS: {e}', showarrow=False, xref='paper', yref='paper',
                x=0.5, y=0.5, xanchor='center', yanchor='middle', font=dict(size=14, color='red'),
                bgcolor='rgba(0,0,0,0.7)', bordercolor='red', borderwidth=1
            )]
        )
        return fig

# Health Sensor Charts
@app.callback(
    Output('heartrate-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_heartrate_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['heartRate']:
        # Filter out None values
        valid_data = [(t, hr) for t, hr in zip(health_data['timestamps'], health_data['heartRate']) if hr is not None]
        if valid_data:
            timestamps, heart_rates = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=heart_rates,
                mode='lines+markers',
                name='Heart Rate',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=6, color='#e74c3c'),
                fill='tonexty',
                fillcolor='rgba(231, 76, 60, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "❤ Heart Rate Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Heart Rate (BPM)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('spo2-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_spo2_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['spo2']:
        # Filter out None values
        valid_data = [(t, spo2) for t, spo2 in zip(health_data['timestamps'], health_data['spo2']) if spo2 is not None]
        if valid_data:
            timestamps, spo2_values = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=spo2_values,
                mode='lines+markers',
                name='SpO2',
                line=dict(color='#3498db', width=3),
                marker=dict(size=6, color='#3498db'),
                fill='tonexty',
                fillcolor='rgba(52, 152, 219, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "🫁 SpO2 Oxygen Saturation - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="SpO2 (%)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('temperature-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_temperature_chart(n):
    env_data = data_manager.get_environmental_data()
    
    fig = go.Figure()
    if env_data['timestamps'] and env_data['temperature']:
        # Filter out None values
        valid_data = [(t, temp) for t, temp in zip(env_data['timestamps'], env_data['temperature']) if temp is not None]
        if valid_data:
            timestamps, temperatures = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=temperatures,
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#f39c12', width=3),
                marker=dict(size=6, color='#f39c12'),
                fill='tonexty',
                fillcolor='rgba(243, 156, 18, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "🌡 Temperature Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('humidity-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_humidity_chart(n):
    env_data = data_manager.get_environmental_data()
    
    fig = go.Figure()
    if env_data['timestamps'] and env_data['humidity']:
        # Filter out None values
        valid_data = [(t, hum) for t, hum in zip(env_data['timestamps'], env_data['humidity']) if hum is not None]
        if valid_data:
            timestamps, humidity_values = zip(*valid_data)
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=humidity_values,
                mode='lines+markers',
                name='Humidity',
                line=dict(color='#2980b9', width=3),
                marker=dict(size=6, color='#2980b9'),
                fill='tonexty',
                fillcolor='rgba(41, 128, 185, 0.1)'
            ))
    
    fig.update_layout(
        title={
            'text': "💧 Humidity Monitor - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="Humidity (%)",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

@app.callback(
    Output('gsr-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_gsr_chart(n):
    health_data = data_manager.get_health_data()
    
    fig = go.Figure()
    if health_data['timestamps'] and health_data['GSR']:
        fig.add_trace(go.Scatter(
            x=list(health_data['timestamps']),
            y=list(health_data['GSR']),
            mode='lines+markers',
            name='GSR',
            line=dict(color='#27ae60', width=3),
            marker=dict(size=6, color='#27ae60'),
            fill='tonexty',
            fillcolor='rgba(39, 174, 96, 0.1)'
        ))
    
    fig.update_layout(
        title={
            'text': "✋ GSR (Galvanic Skin Response) - Real-time",
            'x': 0.5,
            'font': {'color': '#ffffff', 'size': 16}
        },
        xaxis_title="Time",
        yaxis_title="GSR Level",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        xaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        ),
        yaxis=dict(
            gridcolor='#636e72',
            tickfont={'color': '#ffffff'}
        )
    )
    return fig

# ---------------------------
# Navigation Callbacks for Multi-page Flow
# ---------------------------

# Node selection callback (from nodes page to vitals)
@app.callback(
    [Output('selected-node-store','data'), Output('url','pathname', allow_duplicate=True)],
    Input({'type': 'node-select-btn', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def select_node(n_clicks_list):
    if not any(n_clicks_list) or not callback_context.triggered:
        return dash.no_update, dash.no_update
    
    # Get the node ID that was clicked
    button_id = callback_context.triggered[0]['prop_id']
    node_id = eval(button_id.split('.')[0])['index']  # Extract node ID
    
    return {'node': node_id}, '/vitals'

# Back to zones callback (from nodes page)
@app.callback(
    Output('url','pathname', allow_duplicate=True),
    Input('back-to-zones-btn','n_clicks'),
    prevent_initial_call=True
)
def back_to_zones(n_clicks):
    if n_clicks and n_clicks > 0:
        return '/'
    return dash.no_update

# Update selected node display in RFID section
@app.callback(
    Output('selected-node-display','children'),
    Input('selected-node-store','data')
)
def update_selected_node_display(node_data):
    if node_data and 'node' in node_data:
        return f"Node {node_data['node']}"
    return "No node selected"

# Update RFID checkpoint progress display
@app.callback(
    [Output('checkpoint-flow-diagram','children'), Output('latest-rfid-scan','children')],
    [Input('interval-component','n_intervals'), Input('selected-node-store','data')],
    prevent_initial_call=True
)
def update_rfid_checkpoint_display(n, node_data):
    try:
        # If the callback was triggered by selecting a node, reset checkpoint
        # progress for that node so the UI shows unscanned (red) states on load.
        ctx = callback_context
        if ctx.triggered and ctx.triggered[0]['prop_id'].startswith('selected-node-store'):
            try:
                sel_node = node_data.get('node') if node_data and 'node' in node_data else None
                if sel_node:
                    logging.info(f"Resetting checkpoint progress for node view: {sel_node}")
                    # Reset checkpoint progress for this node
                    data_manager.reset_checkpoint_progress(node_id=sel_node)
                    # Also reset per-tag scan counter for tags that map to this node
                    # (common case: tag id equals node id e.g. 'C7761005')
                    try:
                        data_manager.reset_checkpoint_progress(tag_id=sel_node)
                    except Exception:
                        pass
            except Exception:
                logging.exception("Error while resetting checkpoint progress on node select")

        if not node_data or 'node' not in node_data:
            # Always render the diagram for the four checkpoints, even if no node selected
            default_checkpoints = ['Main Gate Checkpoint', 'Weighbridge Checkpoint', 'Fuel Station Checkpoint', 'Workshop Checkpoint']
            flow_elements = []
            for i, checkpoint_name in enumerate(default_checkpoints):
                circle_style = {
                    'width': '60px',
                    'height': '60px',
                    'borderRadius': '50%',
                    'background': 'linear-gradient(45deg, #dc3545, #ff4444)',
                    'border': '3px solid #ff4444',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'boxShadow': '0 0 10px rgba(255, 68, 68, 0.3)',
                    'position': 'relative',
                    'opacity': '0.7'
                }
                icon = html.I(className="fas fa-times", style={'color': 'white', 'fontSize': '20px'})
                status_info = html.Div([
                    html.Small("PENDING", style={'color': '#ff4444', 'fontWeight': 'bold', 'fontSize': '9px'}),
                    html.Br(),
                    html.Small("Waiting...", style={'color': '#cccccc', 'fontSize': '8px'})
                ], style={'position': 'absolute', 'top': '70px', 'textAlign': 'center', 'whiteSpace': 'nowrap', 'width': '80px'})
                checkpoint_container = html.Div([
                    html.Div([
                        icon,
                    ], style=circle_style),
                    html.Div(checkpoint_name, style={
                        'color': '#ffffff',
                        'fontSize': '11px',
                        'textAlign': 'left',
                        'marginTop': '8px',
                        'fontWeight': 'bold',
                        'maxWidth': '90px',
                        'lineHeight': '1.2',
                        'overflow': 'hidden',
                        'width': '80px',
                        'margin': '0 auto'
                    }),
                    html.Div([
                        html.Small("PENDING", style={'color': '#ff4444', 'fontWeight': 'bold', 'fontSize': '9px'}),
                        html.Br(),
                        html.Small("Waiting...", style={'color': '#cccccc', 'fontSize': '8px'})
                    ], style={'textAlign': 'left', 'whiteSpace': 'nowrap', 'width': '80px', 'margin': '0 auto', 'marginTop': '2px'})
                ], style={'display': 'inline-block', 'margin': '0 15px', 'textAlign': 'center', 'verticalAlign': 'top'})
                flow_elements.append(checkpoint_container)
                if i < len(default_checkpoints) - 1:
                    arrow = html.Div([
                        html.I(className="fas fa-arrow-right", style={
                            'color': '#666666',
                            'fontSize': '18px',
                            'boxShadow': 'none',
                            'textShadow': 'none'
                        })
                    ], style={
                        'display': 'inline-block',
                        'margin': '0 8px',
                        'paddingTop': '25px',
                        'verticalAlign': 'top'
                    })
                    flow_elements.append(arrow)
            flow_diagram = html.Div(flow_elements, style={
                'display': 'flex',
                'alignItems': 'flex-start',
                'justifyContent': 'center',
                'flexWrap': 'nowrap',
                'padding': '15px 10px',
                'minHeight': '140px',
                'overflowX': 'auto'
            })
            return [flow_diagram], "No scans yet"
        
        selected_node = node_data['node']
        
        # Get RFID data from data manager
        rfid_data = data_manager.get_rfid_data()
        
        # Show latest tag scan with station info
        latest_tag = rfid_data.get('latest_tag', 'None')
        latest_station = rfid_data.get('latest_station', 'None')
        
        if latest_tag != 'None' and latest_station != 'None':
            latest_scan_text = f"Station: {latest_station} | Tag: {latest_tag}"
        else:
            latest_scan_text = "No scans yet"
        
        # Get checkpoint status for the selected node
        checkpoint_status = data_manager.get_checkpoint_status(selected_node)
        
        if not checkpoint_status:
            return [html.P(f"No checkpoints configured for Node {selected_node}", 
                          style={'color': '#cccccc', 'textAlign': 'center'})], latest_scan_text
        
        # Create visual flow diagram
        flow_elements = []
        
        for i, (checkpoint_name, is_passed, timestamp) in enumerate(checkpoint_status):
            # Checkpoint circle
            if is_passed:
                circle_style = {
                    'width': '60px',
                    'height': '60px',
                    'borderRadius': '50%',
                    'background': 'linear-gradient(45deg, #28a745, #00ff88)',
                    'border': '3px solid #00ff88',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'boxShadow': '0 0 15px rgba(0, 255, 136, 0.5)',
                    'position': 'relative',
                    'animation': 'pulse 2s infinite'
                }
                icon = html.I(className="fas fa-check", style={'color': 'white', 'fontSize': '20px'})
                status_info = html.Div([
                    html.Small("PASSED", style={'color': '#00ff88', 'fontWeight': 'bold', 'fontSize': '9px'}),
                    html.Br(),
                    html.Small(timestamp.strftime('%H:%M:%S') if timestamp else "", 
                              style={'color': '#cccccc', 'fontSize': '8px'})
                ], style={'position': 'absolute', 'top': '70px', 'textAlign': 'center', 'whiteSpace': 'nowrap', 'width': '80px'})
            else:
                circle_style = {
                    'width': '60px',
                    'height': '60px',
                    'borderRadius': '50%',
                    'background': 'linear-gradient(45deg, #dc3545, #ff4444)',
                    'border': '3px solid #ff4444',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'boxShadow': '0 0 10px rgba(255, 68, 68, 0.3)',
                    'position': 'relative',
                    'opacity': '0.7'
                }
                icon = html.I(className="fas fa-times", style={'color': 'white', 'fontSize': '20px'})
                status_info = html.Div([
                    html.Small("PENDING", style={'color': '#ff4444', 'fontWeight': 'bold', 'fontSize': '9px'}),
                    html.Br(),
                    html.Small("Waiting...", style={'color': '#cccccc', 'fontSize': '8px'})
                ], style={'position': 'absolute', 'top': '70px', 'textAlign': 'center', 'whiteSpace': 'nowrap', 'width': '80px'})
            
            # Checkpoint container
            checkpoint_container = html.Div([
                html.Div([
                    icon,
                ], style=circle_style),
                html.Div(checkpoint_name, style={
                    'color': '#ffffff',
                    'fontSize': '11px',
                    'textAlign': 'left',
                    'marginTop': '8px',
                    'marginLeft': '8px',  # shift right so it's just below the circle
                    'fontWeight': 'bold',
                    'maxWidth': '90px',
                    'lineHeight': '1.2',
                    'overflow': 'hidden',
                    'width': '100%'
                }),
                html.Div([
                    html.Small("PENDING", style={'color': '#ff4444', 'fontWeight': 'bold', 'fontSize': '9px', 'marginLeft': '8px'}),
                    html.Br(),
                    html.Small("Waiting...", style={'color': '#cccccc', 'fontSize': '8px', 'marginLeft': '8px'})
                ], style={'textAlign': 'left', 'whiteSpace': 'nowrap', 'width': '80px', 'margin': '0', 'marginTop': '2px'})
            ], style={'display': 'inline-block', 'margin': '0 15px', 'textAlign': 'left', 'verticalAlign': 'top'})
            
            flow_elements.append(checkpoint_container)
            
            # Add arrow between checkpoints (except after the last one)
            if i < len(checkpoint_status) - 1:
                if is_passed and checkpoint_status[i + 1][1]:  # Both current and next are passed
                    arrow_color = '#00ff88'
                    arrow_glow = '0 0 10px rgba(0, 255, 136, 0.7)'
                elif is_passed:  # Only current is passed
                    arrow_color = '#ffaa00'
                    arrow_glow = '0 0 8px rgba(255, 170, 0, 0.5)'
                else:  # Current not passed
                    arrow_color = '#666666'
                    arrow_glow = 'none'
                
                arrow = html.Div([
                    html.I(className="fas fa-arrow-right", style={
                        'color': arrow_color,
                        'fontSize': '18px',
                        'boxShadow': arrow_glow,
                        'textShadow': arrow_glow
                    })
                ], style={
                    'display': 'inline-block',
                    'margin': '0 8px',
                    'paddingTop': '25px',
                    'verticalAlign': 'top'
                })
                flow_elements.append(arrow)
        
        # Create the flow diagram
        flow_diagram = html.Div(flow_elements, style={
            'display': 'flex',
            'alignItems': 'flex-start',
            'justifyContent': 'center',
            'flexWrap': 'nowrap',
            'padding': '15px 10px',
            'minHeight': '140px',
            'overflowX': 'auto'
        })
        
        return [flow_diagram], latest_scan_text
    
    except Exception as e:
        return [html.P(f"Error loading checkpoint data: {str(e)}", 
                      style={'color': '#ff4444', 'textAlign': 'center'})], "Error"


# Reset checkpoint progress when the vitals page is loaded (or reloaded)
@app.callback(
    Output('checkpoint-reset-store','data'),
    Input('url','pathname'),
    State('selected-node-store','data')
)
def reset_checkpoints_on_page_load(pathname, node_data):
    """Reset checkpoint progress for the selected node when the vitals URL is loaded.

    This runs on initial page load (and when the pathname changes). It ensures the
    checkpoint UI shows unscanned (red) checkpoints after a reload.
    """
    try:
        if pathname and pathname.startswith('/vitals') and node_data and 'node' in node_data:
            sel_node = node_data.get('node')
            if sel_node:
                logging.info(f"Page load: resetting checkpoint progress for node {sel_node}")
                data_manager.reset_checkpoint_progress(node_id=sel_node)
                # Also clear per-tag scan counter if tag equals node id
                try:
                    data_manager.reset_checkpoint_progress(tag_id=sel_node)
                except Exception:
                    pass
    except Exception as e:
        logging.error(f"Error resetting checkpoints on page load: {e}")

    # No actual data needed in this store; return dash.no_update to avoid unnecessary writes
    return dash.no_update


# ---------------------------
# Alerts: monitor and render
# ---------------------------
@app.callback(
    Output('alerts-store', 'data', allow_duplicate=True),
    Input('global-interval', 'n_intervals'),
    [State('alerts-store', 'data'), State('chosen-zone-store', 'data'), State('selected-node-store', 'data')],
    prevent_initial_call=True
)
def monitor_alerts(n, alerts_data, zone_data, node_data):
    """Check latest heart rate and append alert when out of safe range (<20 or >80 BPM)."""
    try:
        if alerts_data is None:
            alerts = []
        else:
            alerts = list(alerts_data)

        # Prefer heartRate from gas latest; fall back to last valid in health series
        latest = data_manager.get_gas_data().get('latest', {})
        hr = latest.get('heartRate', None)
        if hr is None:
            try:
                health = data_manager.get_health_data()
                if health and health.get('heartRate'):
                    # pick last non-None
                    for v in reversed(list(health['heartRate'])):
                        if v is not None:
                            hr = v
                            break
            except Exception:
                pass

        # Log evaluation context for diagnostics - ALWAYS log to see if callback is running
        logging.info(f"Alert monitor running: HR={hr}, n={n}, num_alerts={len(alerts)}")

        # Determine zone and node for context
        zone = (latest.get('zone') or (zone_data.get('zone') if zone_data else None))
        if not zone:
            try:
                rfid_ctx = data_manager.get_rfid_data()
                station = rfid_ctx.get('latest_station')
                if isinstance(station, str) and station:
                    zone = f"Zone {station[0].upper()}"
            except Exception:
                zone = None
        zone = zone or 'Unknown'
        node = node_data.get('node') if node_data else 'Unknown'
        # Prefer user name from latest payload; fall back to last RFID 'latest_name'
        user = latest.get('name') or latest.get('person')
        if not user:
            try:
                rfid_ctx = data_manager.get_rfid_data()
                user = rfid_ctx.get('latest_name') or 'Unknown'
            except Exception:
                user = 'Unknown'

        # Only trigger when we have a numeric HR reading (> 0) and it's out of range per new thresholds
        # Treat 0 or negative as "no reading" to avoid spurious alerts from missing sensors
        if hr is not None and isinstance(hr, (int, float)) and hr > 0 and (hr < 20 or hr > 80):
            if hr < 20:
                issue = f"Low heart rate ({hr} BPM < 20)"
            else:
                issue = f"High heart rate ({hr} BPM > 80)"
            
            logging.info(f"🚨 Alert triggered: {issue} — User: {user}, Zone: {zone}, Node: {node}")
            # Avoid spamming duplicate alerts by ensuring latest alert timestamp differs
            now = datetime.now()
            alert_entry = {
                'ts': now.isoformat(),
                'type': 'HEART_RATE',
                'message': issue,
                'zone': zone,
                'node': node,
                'user': user
            }

            # If last alert is identical in message and node within 5 seconds, skip
            if not alerts:
                alerts.append(alert_entry)
            else:
                try:
                    last_ts = datetime.fromisoformat(alerts[-1]['ts'])
                    if not (alerts[-1]['type'] == alert_entry['type'] and alerts[-1]['node'] == alert_entry['node'] and alerts[-1]['message'] == alert_entry['message'] and (last_ts > now - timedelta(seconds=5))):
                        alerts.append(alert_entry)
                except Exception:
                    alerts.append(alert_entry)

        return alerts
    except Exception as e:
        logging.error(f"Error in monitor_alerts: {e}")
        return dash.no_update


# Dedicated clear for Alerts on vitals page to avoid cross-page Input dependency
@app.callback(
    Output('alerts-store', 'data', allow_duplicate=True),
    Input('clear-alerts-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_vitals_alerts(n_clicks):
    if n_clicks and n_clicks > 0:
        return []
    return dash.no_update


@app.callback(
    Output('alerts-list', 'children'),
    [Input('alerts-store', 'data'), Input('clear-alerts-btn', 'n_clicks')],
    prevent_initial_call=False
)
def render_alerts(alerts_data, clear_clicks):
    """Render alerts into the Alerts card. Clear button resets to empty."""
    try:
        # If clear button pressed, reset display
        ctx = callback_context
        if ctx.triggered and ctx.triggered[0]['prop_id'].startswith('clear-alerts-btn'):
            return [html.P("No alerts", style={'color': '#99aab5'})]

        if not alerts_data:
            return [html.P("No alerts", style={'color': '#99aab5'})]

        # Build list of alert rows (most recent first)
        rows = []
        for a in reversed(list(alerts_data))[-10:]:
            ts = a.get('ts')
            try:
                ts_fmt = datetime.fromisoformat(ts).strftime('%H:%M:%S')
            except Exception:
                ts_fmt = ts
            rows.append(html.Div([
                html.Span(f"[{ts_fmt}] ", style={'color': '#ffcc00', 'fontWeight': '700'}),
                html.Strong(a.get('message', ''), style={'color': '#ffffff'}),
                html.Span(f" — User: {a.get('user', 'Unknown')}", style={'color': '#ffd1d1', 'marginLeft': '8px'}),
                html.Span(f" • Zone: {a.get('zone', 'Unknown')}", style={'color': '#ff8888', 'marginLeft': '6px'}),
                html.Span(f" • Node: {a.get('node', 'Unknown')}", style={'color': '#ffaaaa', 'marginLeft': '6px'})
            ], style={'padding': '6px 0', 'borderBottom': '1px solid rgba(255,255,255,0.03)'}))

        return rows
    except Exception as e:
        logging.error(f"Error rendering alerts: {e}")
        return [html.P("Error loading alerts", style={'color': '#ff4444'})]


# Landing page alerts callback (separate from vitals page alerts)
@app.callback(
    Output('landing-alerts-list', 'children'),
    [Input('alerts-store', 'data'), Input('landing-clear-alerts-btn', 'n_clicks')],
    prevent_initial_call=False
)
def render_landing_alerts(alerts_data, clear_clicks):
    """Render alerts into the landing page alerts panel."""
    try:
        # If clear button pressed, reset display
        ctx = callback_context
        if ctx.triggered and ctx.triggered[0]['prop_id'].startswith('landing-clear-alerts-btn'):
            return [html.P("No active alerts", style={'color': '#99aab5', 'textAlign': 'center', 'fontStyle': 'italic'})]

        if not alerts_data:
            return [html.P("No active alerts", style={'color': '#99aab5', 'textAlign': 'center', 'fontStyle': 'italic'})]

        # Build list of alert rows (most recent first, compact format for landing page)
        rows = []
        # Take last 8 alerts and reverse them to show most recent first
        recent_alerts = list(alerts_data)[-8:]
        for a in reversed(recent_alerts):
            ts = a.get('ts')
            try:
                ts_fmt = datetime.fromisoformat(ts).strftime('%H:%M:%S')
            except Exception:
                ts_fmt = ts
            
            # More compact format for landing page
            rows.append(html.Div([
                html.Div([
                    html.I(className="fas fa-exclamation-circle", style={'color': '#ff4444', 'marginRight': '8px'}),
                    html.Strong(a.get('user', 'Unknown'), style={'color': '#ffd1d1'}),
                    html.Span(" • ", style={'color': '#ffaaaa', 'margin': '0 6px'}),
                    html.Strong(f"{a.get('zone', 'Unknown')}", style={'color': '#ff8888'}),
                    html.Span(f" • Node {a.get('node', 'Unknown')}", style={'color': '#ffaaaa'})
                ], style={'marginBottom': '4px'}),
                html.Div([
                    html.Span(f"[{ts_fmt}] ", style={'color': '#ffcc00', 'fontSize': '0.85rem'}),
                    html.Span(a.get('message', ''), style={'color': '#ffffff', 'fontSize': '0.85rem'})
                ])
            ], style={
                'padding': '12px',
                'marginBottom': '8px',
                'background': 'rgba(255, 68, 68, 0.1)',
                'border': '1px solid rgba(255, 68, 68, 0.3)',
                'borderRadius': '8px',
                'borderLeft': '4px solid #ff4444'
            }))

        return rows
    except Exception as e:
        import traceback
        logging.error(f"Error rendering landing alerts: {e}\n{traceback.format_exc()}")
        return [html.P("Error loading alerts", style={'color': '#ff4444', 'textAlign': 'center'})]


# Clear alerts callback (handles both clear buttons)
@app.callback(
    Output('alerts-store', 'data', allow_duplicate=True),
    Input('landing-clear-alerts-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_landing_alerts(n_clicks):
    """Clear alerts when landing page clear button is clicked."""
    if n_clicks and n_clicks > 0:
        return []  # Clear all alerts
    return dash.no_update


if __name__ == '__main__':
    try:
        # Connect to MQTT broker in background so server startup isn't blocked
        # (network/DNS delays can make a blocking connect hang for many seconds)
        threading.Thread(target=mqtt_client.connect, daemon=True).start()

        # Small pause to let background thread initiate (non-blocking)
        time.sleep(0.2)

        print("🛡 Starting Mine Armour Multi-Sensor Dashboard...")
        print("📊 Dashboard will be available at: http://localhost:8050")
        print("🔄 Real-time updates every second")
        print(f"📡 MQTT Topic: {mqtt_client.gas_topic} (Multi-Sensor Data)")
        print("🔥 Gas Sensors: LPG, CH4, Propane, Butane, H2")
        print("❤ Health Sensors: Heart Rate, SpO2, GSR, Stress")
        print("🌡 Environment: Temperature, Humidity")
        print("📍 GPS: Location tracking")

        # Run the dashboard (disable dev tools UI/hot-reload in production to remove debug overlay)
        app.run_server(debug=False, dev_tools_ui=False, dev_tools_hot_reload=False, host='0.0.0.0', port=8050)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Mine Armour Dashboard...")
        mqtt_client.disconnect()
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        mqtt_client.disconnect()