# Mine Armour SMS Alert System Setup

## Overview
The Mine Armour system now includes real-time SMS alerts for critical safety conditions:
- **Heart Rate Alerts**: Low (<60 BPM) or High (>100 BPM) heart rate readings
- **Gas Sensor Alerts**: Dangerous gas levels exceeding safety thresholds
  - LPG: >1000 ppm
  - CH4: >5000 ppm  
  - Propane: >1000 ppm
  - Butane: >1000 ppm
  - H2: >4000 ppm

## Twilio Setup Instructions

### 1. Create Twilio Account
1. Go to [https://www.twilio.com/](https://www.twilio.com/)
2. Sign up for a free account
3. Verify your phone number (9677091290)

### 2. Get Twilio Credentials
After logging into Twilio Console:
1. **Account SID**: Found on your Twilio Console Dashboard
2. **Auth Token**: Found on your Twilio Console Dashboard (click "Show" to reveal)
3. **Phone Number**: Purchase a Twilio phone number or use the trial number

### 3. Configure Environment Variables
Update your `.env` file with your Twilio credentials:

```env
# SMS Alert Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_actual_account_sid_here
TWILIO_AUTH_TOKEN=your_actual_auth_token_here  
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
ALERT_PHONE_NUMBER=+919677091290  # Your mobile number (already configured)
```

### 4. Example Credentials Format
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your32characterauthtokenxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890x
ALERT_PHONE_NUMBER=+91xxxxxxxxxx
```

## SMS Message Format
When an alert is triggered, you'll receive an SMS like this:

```
🛡 MINE ARMOUR ALERT 🛡

⚠️ HEART_RATE: High heart rate (105 BPM > 100)

👤 User: SUSHMA
📍 Zone: Zone A
🔗 Node: C7761005
🕐 Time: 2026-01-24 15:30:45

Immediate action required!
```

## Features
- **Duplicate Prevention**: Same alert won't be sent again within 30 seconds
- **Real-time Monitoring**: Alerts checked every 3 seconds
- **Comprehensive Data**: Includes user, zone, node, and timestamp
- **Multi-sensor Support**: Heart rate + all 5 gas sensors monitored
- **Error Handling**: Graceful fallback if SMS service unavailable

## Testing the SMS System
1. Run the dashboard: `python mine_armour_dashboard.py`
2. Check logs for "✅ Twilio SMS client initialized successfully"
3. Monitor real-time sensor data - alerts trigger automatically when thresholds are exceeded

## Troubleshooting
1. **"Twilio credentials not found"**: Check your .env file
2. **"Failed to initialize Twilio client"**: Verify Account SID and Auth Token
3. **"SMS alert skipped"**: Twilio client not initialized, check credentials
4. **No SMS received**: Check phone number format (+919677091290) and Twilio balance

## Free Trial Limitations
- Twilio free trial includes $15 credit
- SMS costs ~$0.0075 per message
- You can send ~2000 free SMS alerts
- All SMS will have "Sent from your Twilio trial account" prefix

## Upgrade to Production
For production use:
1. Upgrade your Twilio account (remove trial restrictions)  
2. Purchase a dedicated phone number
3. Set up billing for continuous service
4. Consider SMS delivery confirmations