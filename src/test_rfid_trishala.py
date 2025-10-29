#!/usr/bin/env python3
"""
Test RFID checkpoint progression for tag 93BA302D (TRISHALA)
This simulates RFID scans with station_id A1 and tag_id 93BA302D
"""
from mine_armour_dashboard import data_manager
import pprint
import time

print('=' * 60)
print('TESTING RFID FOR TAG: 93BA302D (TRISHALA) at Station A1')
print('=' * 60)

# Simulate multiple scans to test forward and reverse progression
test_scans = [
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
    {'station_id': 'A1', 'tag_id': '93BA302D', 'name': 'TRISHALA'},
]

pp = pprint.PrettyPrinter(indent=2)

for i, scan_data in enumerate(test_scans, 1):
    print(f'\n--- Scan #{i} ---')
    print(f'Simulating scan: {scan_data}')
    data_manager.add_rfid_data(scan_data)
    
    # Small delay to avoid debouncing (3 second debounce window)
    time.sleep(3.1)
    
    # Get current checkpoint progress
    rfid = data_manager.get_rfid_data()
    checkpoint_progress = rfid.get('checkpoint_progress', {})
    
    print(f'\nCheckpoint Progress for NODE 93BA302D:')
    if '93BA302D' in checkpoint_progress:
        pp.pprint(checkpoint_progress['93BA302D'])
    else:
        print('  No progress yet')
    
    print(f'\nLatest Tag: {rfid.get("latest_tag")}')
    print(f'Latest Station: {rfid.get("latest_station")}')
    print(f'Latest Name: {rfid.get("latest_name")}')

print('\n' + '=' * 60)
print('FINAL CHECKPOINT PROGRESS FOR ALL NODES:')
print('=' * 60)
rfid = data_manager.get_rfid_data()
pp.pprint(rfid.get('checkpoint_progress'))

print('\n' + '=' * 60)
print('ALL RFID SCANS:')
print('=' * 60)
for scan in rfid.get('uid_scans'):
    print(f"  Tag: {scan['tag_id']}, Station: {scan['station_id']}, "
          f"Node: {scan['node_id']}, Checkpoint: {scan['checkpoint']}, "
          f"Time: {scan['timestamp'].strftime('%H:%M:%S')}")
