#!/usr/bin/env python3
"""
Mine Armour Dashboard Launcher
Quick start script for the real-time sensor dashboard
"""

import os
import sys
import subprocess
import time

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'dash',
        'plotly', 
        'paho-mqtt',
        'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print("pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print(f"❌ Environment file '{env_file}' not found")
        print("📝 Create a .env file with your MQTT broker settings")
        return False
    
    required_vars = ['MQTT_HOST', 'MQTT_PORT', 'MQTT_USERNAME', 'MQTT_PASSWORD']
    missing_vars = []
    
    with open(env_file, 'r') as f:
        content = f.read()
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    return True

def main():
    print("🛡️  MINE ARMOUR DASHBOARD LAUNCHER")
    print("=" * 50)
    
    # Check requirements
    print("🔍 Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    # Check environment file
    print("📄 Checking environment configuration...")
    if not check_env_file():
        sys.exit(1)
    
    print("✅ All checks passed!")
    print("\n🚀 Starting Mine Armour Dashboard...")
    print("📊 Dashboard URL: http://localhost:8050")
    print("🔄 Real-time updates every second")
    print("🛑 Press Ctrl+C to stop the dashboard\n")
    
    try:
        # Start the dashboard
        subprocess.run([sys.executable, 'mine_armour_dashboard.py'])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()
