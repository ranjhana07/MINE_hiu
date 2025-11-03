#!/usr/bin/env python3
"""DISABLED: Local RFID simulation is not allowed.

This script has been intentionally disabled to ensure only real MQTT data
affects checkpoint progression. Please publish real scans to the 'rfid' topic
from hardware devices.
"""
import sys
sys.exit("This RFID test script is disabled. Use real MQTT device data.")
