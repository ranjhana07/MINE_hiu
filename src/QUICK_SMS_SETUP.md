# Mine Armour SMS Alert System - Quick Setup Guide

## ✅ What's Been Implemented

Your Mine Armour system now has **real-time SMS alerts** that will send text messages to **+919677091290** when dangerous conditions are detected.

### 🚨 Alert Triggers
- **Heart Rate**: Low (<80 BPM) or High (>100 BPM)
- **Temperature**: Low (<22°C) or High (>28°C)  
- **Gas Dangers**: 
  - LPG > 1000 ppm
  - CH4 > 5000 ppm
  - Propane > 1000 ppm  
  - Butane > 1000 ppm
  - H2 > 4000 ppm

## 🛠️ Setup Steps (Required)

### 1. Get Twilio Account (FREE)
1. Go to https://www.twilio.com and sign up
2. Verify your phone number: **9677091290**
3. Get your credentials from the Twilio Console

### 2. Update .env File
Edit `src/.env` and replace these lines:
```
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here  
TWILIO_PHONE_NUMBER=your_twilio_phone_number_here
```

With your actual Twilio values:
```
TWILIO_ACCOUNT_SID=AC1234567890abcdef...
TWILIO_AUTH_TOKEN=your32chartoken...
TWILIO_PHONE_NUMBER=+12345678901
```

*(Your phone number +919677091290 is already configured)*

### 3. Test the System
```bash
cd src
python mine_armour_dashboard.py    # Start dashboard - real-time monitoring only
```

## 📱 What You'll Receive

When an alert happens, you'll get an SMS like:

```
🛡 MINE ARMOUR ALERT 🛡

⚠️ HEART_RATE: High heart rate (105 BPM > 100)

👤 User: SUSHMA
📍 Zone: Zone A  
🔗 Node: C7761005
🕐 Time: 2026-01-24 15:30:45

Immediate action required!
```

Or for temperature:

```
🛡 MINE ARMOUR ALERT 🛡

⚠️ TEMPERATURE: High temperature (30°C > 28°C)

👤 User: TRISHALA
📍 Zone: Zone B  
🔗 Node: 93BA302D
🕐 Time: 2026-01-24 15:31:20

Immediate action required!
```

## 🔧 Files Added/Modified

✅ **mine_armour_dashboard.py** - Added SMS integration  
✅ **dashboard_requirements.txt** - Added twilio dependency  
✅ **.env** - Added Twilio configuration  
✅ **test_sms.py** - SMS testing tool  
✅ **simulate_alerts.py** - Alert testing tool  
✅ **SMS_SETUP.md** - Detailed setup instructions  

## 🎯 Real-Time Monitoring

**Start the dashboard**: `python mine_armour_dashboard.py`

The system will automatically monitor real-time sensor data and send SMS alerts when thresholds are exceeded. No manual testing needed - alerts trigger automatically from live sensor data!

## 💰 Cost

- Twilio free trial: $15 credit (~2000 SMS)
- Production cost: ~$0.0075 per SMS
- Your implementation: **Cost-effective safety monitoring**

## 🚨 Emergency Features

- **30-second cooldown**: Prevents SMS spam
- **Duplicate detection**: Same alert won't repeat
- **Real-time monitoring**: 3-second check intervals  
- **Comprehensive data**: User, zone, node info in every alert
- **Fallback handling**: System continues working if SMS fails

## ⚡ Next Steps

1. Set up your Twilio account (5 minutes)
2. Update the .env file with your credentials  
3. Start real-time monitoring: `python mine_armour_dashboard.py`
4. Monitor with confidence - alerts trigger automatically from live sensor data!

Your miners' safety is now backed by instant SMS notifications from real-time sensor monitoring! 🛡️📱