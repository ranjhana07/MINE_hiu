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
from datetime import datetime
from collections import deque
import logging

# Third-party imports
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
import plotly.express as px
import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context
import dash_bootstrap_components as dbc
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
                    # Zone B checkpoints
                    '2001': ['North Entry', 'Equipment Room', 'Gas Detection', 'Exit Portal'],
                    '2055': ['Central Hub', 'Safety Station', 'Mining Zone'],
                    '2089': ['Secondary Tunnel', 'Emergency Bay', 'Final Check'],
                    # Zone C checkpoints
                    '3012': ['South Gate', 'Tool Center', 'Deep Shaft', 'Return Path'],
                    '3067': ['Control Point', 'Ventilation Room', 'Safety Exit'],
                    '3134': ['Access Tunnel', 'Equipment Bay', 'Emergency Station']
                }
            }
        }
        self.lock = threading.Lock()
    
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
            
            # Map station_id to node_id and checkpoint (you can customize this mapping)
            # Station format examples: A1, A2, B1, B2, etc.
            zone = station_id[0] if station_id else ''  # Extract zone letter (A, B, C)
            station_num = station_id[1:] if len(station_id) > 1 else '1'  # Extract station number
            
            # Map zones to node IDs
            zone_nodes = {
                'A': ['1298', '1753', '1456'],
                'B': ['2001', '2055', '2089'], 
                'C': ['3012', '3067', '3134']
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
                'A1': 'Entry Gate',
                'A2': 'Safety Check', 
                'A3': 'Equipment Bay',
                'A4': 'Deep Section',
                'B1': 'North Entry',
                'B2': 'Equipment Room',
                'B3': 'Gas Detection', 
                'B4': 'Exit Portal',
                'C1': 'South Gate',
                'C2': 'Tool Center',
                'C3': 'Deep Shaft',
                'C4': 'Return Path'
            }
            checkpoint_id = checkpoint_mapping.get(station_id, f'Station {station_id}')
            
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
            
            # Update checkpoint progress for specific nodes
            if node_id and checkpoint_id:
                if node_id not in self.data['rfid_checkpoints']['checkpoint_progress']:
                    self.data['rfid_checkpoints']['checkpoint_progress'][node_id] = {}
                
                self.data['rfid_checkpoints']['checkpoint_progress'][node_id][checkpoint_id] = timestamp
            
            logging.info(f"RFID checkpoint updated: Station={station_id}, Tag={tag_id}, Node={node_id}, Checkpoint={checkpoint_id}")
    
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
        
        # MQTT Topics
        self.gas_topic = "LOKI_2004"
        self.rfid_topic = "rfid"  # RFID checkpoint topic
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info("Connected to MQTT broker")
            # Subscribe to gas sensor topic
            client.subscribe(self.gas_topic)
            logging.info(f"Subscribed to {self.gas_topic}")
            # Subscribe to RFID checkpoint topic
            client.subscribe(self.rfid_topic)
            logging.info(f"Subscribed to {self.rfid_topic}")
        else:
            logging.error(f"Failed to connect to MQTT broker: {rc}")
    
    def on_message(self, client, userdata, message):
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')
            
            if topic == self.gas_topic:
                # Parse gas sensor JSON data
                data = json.loads(payload)
                self.data_manager.add_gas_data(data)
                logging.info(f"Received gas data: {data}")
                
            elif topic == self.rfid_topic:
                # Parse RFID checkpoint data
                data = json.loads(payload)
                self.data_manager.add_rfid_data(data)
                logging.info(f"Received RFID data: {data}")
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.info("Disconnected from MQTT broker")
    
    def connect(self):
        try:
            # Fix: Add callback_api_version parameter for newer paho-mqtt versions
            self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
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
<html>
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
    dcc.Store(id='selected-node-store', storage_type='session'),
    dcc.Store(id='auth-store', storage_type='session'),
    html.Div(id='page-content')
])

# ---------------------------
# Page: Zone Selection
# ---------------------------
def zone_select_layout():
    # Full screen centered flex container
    return html.Div([
        html.Div([
            html.Div([
                html.H1("MINE ARMOUR", className='landing-title'),
                html.Div("Protecting Miners Preserving Lives", className='landing-subtext', style={'fontSize':'0.95rem','marginTop':'-18px','marginBottom':'10px','letterSpacing':'.8px','color':'#ffcccc','fontWeight':'600'}),
                dcc.Dropdown(
                    id='zone-select-only',
                    options=[
                        {'label':'Zone A','value':'ZONE_A'},
                        {'label':'Zone B','value':'ZONE_B'},
                        {'label':'Zone C','value':'ZONE_C'}
                    ],
                    value='ZONE_A',
                    clearable=False,
                    placeholder='Select Zone',
                    className='landing-dropdown'
                ),
                html.Button("TRACK", id='go-to-vitals-btn', n_clicks=0, className='landing-btn'),
                html.Div(id='zone-select-msg', className='landing-subtext')
            ], className='landing-card')
        ], className='landing-wrapper')
    ])

# ---------------------------
# Page: Nodes Selection 
# ---------------------------
def nodes_layout(zone_name):
    # Get nodes for the selected zone
    zone_nodes = {
        'ZONE_A': [
            {'id': '1298', 'name': 'Node 1298', 'status': 'Active'},
            {'id': '1753', 'name': 'Node 1753', 'status': 'Active'},
            {'id': '1456', 'name': 'Node 1456', 'status': 'Active'}
        ],
        'ZONE_B': [
            {'id': '2001', 'name': 'Node 2001', 'status': 'Active'},
            {'id': '2055', 'name': 'Node 2055', 'status': 'Active'},
            {'id': '2089', 'name': 'Node 2089', 'status': 'Active'}
        ],
        'ZONE_C': [
            {'id': '3012', 'name': 'Node 3012', 'status': 'Active'},
            {'id': '3067', 'name': 'Node 3067', 'status': 'Active'},
            {'id': '3134', 'name': 'Node 3134', 'status': 'Active'}
        ]
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
                    "MQTT Topic: LOKI_2004 | ",
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
                        html.I(className="fas fa-id-card me-2", style={'color': '#ff6b6b'}),
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
        interval=1000,  # Update every second
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
    # Not authenticated -> always show login
    if not auth_data:
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
    [Output('chosen-zone-store','data'), Output('zone-select-msg','children'), Output('url','pathname')],
    Input('go-to-vitals-btn','n_clicks'),
    State('zone-select-only','value'),
    prevent_initial_call=True
)
def go_to_nodes(n, zone_value):
    if not zone_value:
        return dash.no_update, 'Please choose a zone.', dash.no_update
    return {'zone': zone_value}, '', '/nodes'

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
        if not node_data or 'node' not in node_data:
            return [html.P("Select a node to view checkpoint flow", 
                          style={'color': '#999999', 'fontStyle': 'italic', 'textAlign': 'center'})], "No scans yet"
        
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
                    status_info
                ], style=circle_style),
                html.Div(checkpoint_name, style={
                    'color': '#ffffff',
                    'fontSize': '11px',
                    'textAlign': 'center',
                    'marginTop': '35px',
                    'fontWeight': 'bold',
                    'maxWidth': '90px',
                    'lineHeight': '1.2',
                    'overflow': 'hidden'
                })
            ], style={'display': 'inline-block', 'margin': '0 15px', 'textAlign': 'center', 'verticalAlign': 'top'})
            
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


if __name__ == '__main__':
    try:
        # Connect to MQTT broker
        mqtt_client.connect()
        
        # Wait a moment for connection
        time.sleep(2)
        
        print("🛡 Starting Mine Armour Multi-Sensor Dashboard...")
        print("📊 Dashboard will be available at: http://localhost:8050")
        print("🔄 Real-time updates every second")
        print("📡 MQTT Topic: LOKI_2004 (Multi-Sensor Data)")
        print("🔥 Gas Sensors: LPG, CH4, Propane, Butane, H2")
        print("❤ Health Sensors: Heart Rate, SpO2, GSR, Stress")
        print("🌡 Environment: Temperature, Humidity")
        print("📍 GPS: Location tracking")
        
        # Run the dashboard
        app.run_server(debug=True, host='0.0.0.0', port=8050)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Mine Armour Dashboard...")
        mqtt_client.disconnect()
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        mqtt_client.disconnect()