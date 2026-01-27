#!/usr/bin/env python3
"""
Twilio SMS Test - Check SMS configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔍 TWILIO CONFIGURATION CHECK")
print("=" * 50)

# Get credentials
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')  
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
ALERT_PHONE_NUMBER = os.getenv('ALERT_PHONE_NUMBER')

print(f"📱 TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID[:10]}..." if TWILIO_ACCOUNT_SID else "❌ TWILIO_ACCOUNT_SID: NOT FOUND")
print(f"🔐 TWILIO_AUTH_TOKEN: {'*' * 10}" if TWILIO_AUTH_TOKEN else "❌ TWILIO_AUTH_TOKEN: NOT FOUND")
print(f"📞 TWILIO_PHONE_NUMBER: {TWILIO_PHONE_NUMBER}" if TWILIO_PHONE_NUMBER else "❌ TWILIO_PHONE_NUMBER: NOT FOUND")
print(f"📱 ALERT_PHONE_NUMBER: {ALERT_PHONE_NUMBER}" if ALERT_PHONE_NUMBER else "❌ ALERT_PHONE_NUMBER: NOT FOUND")

print("\n🧪 TESTING TWILIO CONNECTION...")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ALERT_PHONE_NUMBER]):
    print("❌ Missing credentials - check your .env file")
    exit(1)

try:
    from twilio.rest import Client
    print("✅ Twilio library imported")
    
    # Test client initialization
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    print("✅ Twilio client created")
    
    # Test account info (this will validate credentials)
    account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
    print(f"✅ Account verified: {account.friendly_name}")
    
    # Try to send a test SMS
    print(f"\n📤 Attempting test SMS...")
    print(f"FROM: {TWILIO_PHONE_NUMBER}")
    print(f"TO: {ALERT_PHONE_NUMBER}")
    
    message = client.messages.create(
        body="🛡 Mine Armour SMS Test - This is a test message. Reply STOP to opt out.",
        from_=TWILIO_PHONE_NUMBER,
        to=ALERT_PHONE_NUMBER
    )
    
    print(f"✅ SMS sent successfully!")
    print(f"📄 Message SID: {message.sid}")
    print(f"📊 Status: {message.status}")
    print(f"📱 Check your phone: {ALERT_PHONE_NUMBER}")
    
except ImportError:
    print("❌ Twilio library not installed. Run: pip install twilio")
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"❌ Error type: {type(e).__name__}")
    
    # Common error diagnostics
    error_str = str(e).lower()
    if "authenticate" in error_str:
        print("💡 Check your Account SID and Auth Token")
    elif "phone number" in error_str:
        print("💡 Check phone number format and Twilio phone number")
    elif "unverified" in error_str:
        print("💡 Phone numbers need to be verified in Twilio trial account")
        print(f"💡 Go to Twilio Console > Phone Numbers > Verified Numbers")
        print(f"💡 Add and verify: {ALERT_PHONE_NUMBER}")
    
print("\n" + "=" * 50)