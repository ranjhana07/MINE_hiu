# RFID Checkpoint System - Configuration Guide

## Overview
The RFID checkpoint system tracks workers' progress through mine checkpoints. Two special tags have enhanced sequential progression tracking:
- **C7761005** - SUSHMA
- **93BA302D** - TRISHALA

## How It Works

### Standard RFID Tags
For normal tags, each RFID scan at a station marks that checkpoint as completed for the assigned node.

### Enhanced Tags (C7761005 & 93BA302D)
These tags use a **forward-then-reverse cycle** through checkpoints:
1. **First 4 scans**: Progress forward through checkpoints 1 → 2 → 3 → 4
2. **Next 4 scans**: Reverse and unmark checkpoints 4 → 3 → 2 → 1
3. **Cycle repeats** indefinitely

## Checkpoint Configuration

### Zone A Checkpoints
Both enhanced tags use the same checkpoints:
1. Main Gate Checkpoint
2. Weighbridge Checkpoint
3. Fuel Station Checkpoint
4. Workshop Checkpoint

## Station to Node Mapping

### Station A1
- **station_id**: `"A1"`
- Maps to the first node in Zone A rotation
- Used for TRISHALA (93BA302D) testing

### Format
```json
{
  "station_id": "A1",
  "tag_id": "93BA302D",
  "name": "TRISHALA"
}
```

## Testing RFID for TRISHALA (93BA302D)

### Method 1: Local Python Test (No MQTT)
Run the local test script:
```bash
python test_rfid_trishala.py
```

This simulates 8 RFID scans and shows checkpoint progression in the console.

### Method 2: MQTT Publishing (Real-time)
Publish RFID messages to the MQTT broker:
```bash
python publish_rfid_trishala.py
```

This publishes 8 RFID scans with 4-second intervals to avoid debouncing.

### Method 3: Manual MQTT Publishing
Use the generic test publisher:
```bash
python test_publish_rfid.py --station A1 --tag 93BA302D
```

Run this command multiple times (wait 4 seconds between runs) to see progression.

### Method 4: HTTP Endpoint (Dashboard must be running)
Send POST request to simulate RFID scan:
```bash
curl -X POST http://localhost:8050/simulate_rfid \
  -H "Content-Type: application/json" \
  -d '{"station_id":"A1","tag_id":"93BA302D","name":"TRISHALA"}'
```

## Expected Behavior

### Scan Progression for 93BA302D (TRISHALA)
| Scan # | Checkpoint State | Description |
|--------|------------------|-------------|
| 1 | ✓ Main Gate | First checkpoint marked |
| 2 | ✓ Main Gate, ✓ Weighbridge | Second checkpoint marked |
| 3 | ✓ Main Gate, ✓ Weighbridge, ✓ Fuel Station | Third checkpoint marked |
| 4 | ✓ All 4 checkpoints | All checkpoints marked |
| 5 | ✓ Main Gate, ✓ Weighbridge, ✓ Fuel Station | Workshop unmarked |
| 6 | ✓ Main Gate, ✓ Weighbridge | Fuel Station unmarked |
| 7 | ✓ Main Gate | Weighbridge unmarked |
| 8 | (empty) | Main Gate unmarked - cycle complete |
| 9 | ✓ Main Gate | **Cycle restarts** |

## Debouncing
The system ignores duplicate scans within **3 seconds** to prevent accidental double-scans.

## Dashboard Usage

### 1. Login
- Username: `admin`
- Password: `admin123`

### 2. Select Zone
Click **"ENTER Zone A"**

### 3. Select Node
Click **"SELECT NODE"** on the card for **NODE 93BA302D - TRISHALA**

### 4. View Checkpoint Progress
The dashboard shows:
- **RFID Checkpoint Progress** section with visual indicators
- Green checkmarks for completed checkpoints
- Real-time updates as RFID scans are received

## Resetting Checkpoint Progress

### Method 1: Via HTTP Endpoint
Reset all progress for a specific node:
```bash
curl -X POST http://localhost:8050/reset_rfid_counter \
  -H "Content-Type: application/json" \
  -d '{"node_id":"93BA302D"}'
```

Reset all progress:
```bash
curl -X POST http://localhost:8050/reset_rfid_counter \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Method 2: Via Python Script
```bash
python reset_rfid_progress.py
```

## Configuration in Code

### Adding More Enhanced Tags
Edit `mine_armour_dashboard.py`, find the `add_rfid_data` method and update:

```python
if tag_lc in ['c7761005', '93ba302d', 'newtag123']:  # Add your new tag here
    target_node = 'C7761005' if tag_lc == 'c7761005' else \
                  '93BA302D' if tag_lc == '93ba302d' else \
                  'NEWTAG123'  # Add mapping
```

### Customizing Checkpoints
Edit the `active_checkpoints` dictionary in `SensorDataManager.__init__`:

```python
'active_checkpoints': {
    '93BA302D': [
        'Main Gate Checkpoint',
        'Weighbridge Checkpoint', 
        'Fuel Station Checkpoint',
        'Workshop Checkpoint'
    ],
    # Add more nodes...
}
```

## Troubleshooting

### RFID scans not showing up
1. Check MQTT connection status in dashboard header
2. Verify MQTT credentials in `.env` file
3. Check that topic is `rfid` (lowercase)
4. Ensure JSON format is correct

### Checkpoints not progressing
1. Wait at least 3 seconds between scans (debouncing)
2. Verify tag_id matches exactly: `93BA302D` (case-insensitive)
3. Check console logs for RFID messages

### Reset not working
1. Ensure dashboard is running
2. Check that node_id matches: `93BA302D`
3. Reload the dashboard page after reset

## MQTT Topic Structure

### RFID Messages
- **Topic**: `rfid`
- **Format**: `{"station_id": "A1", "tag_id": "93BA302D", "name": "TRISHALA"}`
- **QoS**: 1 (recommended)

## Files Reference

- `mine_armour_dashboard.py` - Main dashboard with RFID logic
- `test_rfid_trishala.py` - Local test script for 93BA302D
- `publish_rfid_trishala.py` - MQTT publisher for 93BA302D
- `test_publish_rfid.py` - Generic MQTT publisher (any tag)
- `reset_rfid_progress.py` - Reset checkpoint progress

## Notes

- Tag IDs are **case-insensitive** (93BA302D = 93ba302d)
- Station IDs determine zone mapping (A1 → Zone A)
- Name field is optional but recommended for alerts
- All timestamps are in server local time
- Progress is stored per-node, not per-tag
