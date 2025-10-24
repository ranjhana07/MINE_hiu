# Mine Armour Dashboard - Alerts System

## 🚨 New Feature: Real-time Alerts Panel

The Mine Armour Dashboard now includes a comprehensive alerts system that displays critical safety notifications in real-time.

### 📍 Alert Locations

**1. Landing Page (Zone Selection)**
- **Location**: Right side panel next to zone selection
- **Purpose**: Immediate alert visibility when accessing the dashboard
- **Features**:
  - Compact alert cards with zone and node information
  - Real-time updates every second
  - "Clear All Alerts" button
  - Auto-scrolling for multiple alerts

**2. Vitals Dashboard Page**
- **Location**: Below RFID Checkpoint Status section
- **Purpose**: Detailed alerts during active monitoring
- **Features**:
  - Full alert details with timestamps
  - Zone and node context
  - "Clear Alerts" button
  - Complete alert history

### ⚡ Alert Triggers

**Heart Rate Monitoring**
- **Threshold**: Heart rate > 10 BPM
- **Data Source**: MQTT topic `LOKI_2004`
- **Context**: Automatically includes selected zone and node information
- **Anti-spam**: Prevents duplicate alerts within 5 seconds

### 🎯 Alert Format

**Landing Page Format (Compact):**
```
⚠️ Zone A - Node 1298
[19:56:12] High heart rate: 15 BPM
```

**Vitals Page Format (Detailed):**
```
[19:56:12] High heart rate: 15 BPM — Zone: Zone A Node: 1298
```

### 🔧 How It Works

1. **Data Collection**: MQTT messages on topic `LOKI_2004` are monitored continuously
2. **Threshold Check**: Heart rate values > 10 BPM trigger alerts
3. **Context Addition**: Current zone and selected node are automatically included
4. **Real-time Display**: Alerts appear immediately on both landing and vitals pages
5. **Duplicate Prevention**: Same alerts are suppressed if within 5 seconds

### 🧪 Testing

Use the provided test script to simulate alerts:

```bash
# From project root directory
python src/test_alert_trigger.py
```

This will publish test MQTT messages with heart rates of 15 and 22 BPM to trigger alerts.

### 🎨 Visual Design

- **Theme**: Consistent with existing red-black gradient design
- **Icons**: Font Awesome icons for visual clarity
- **Animation**: Subtle hover effects and transitions
- **Responsive**: Adapts to different screen sizes

### 📱 Usage Flow

1. **Login**: Use `admin` / `admin123`
2. **Landing Page**: See any active alerts in the right panel
3. **Zone Selection**: Choose your monitoring zone
4. **Node Selection**: Select specific worker/node
5. **Vitals Dashboard**: Monitor detailed sensor data and alerts
6. **Alert Management**: Clear alerts as needed

### 🔮 Future Enhancements

- Gas sensor threshold alerts (LPG, CH4, etc.)
- Configurable alert thresholds
- Alert severity levels (Low, Medium, High, Critical)
- Email/SMS notifications
- Alert persistence and logging
- Export alert history

---

**Note**: The alerts system is fully integrated with the existing MQTT infrastructure and requires no additional setup beyond the standard dashboard configuration.