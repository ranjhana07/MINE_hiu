#!/usr/bin/env python3
"""
Reset RFID Checkpoint Progress
Clears checkpoint scan counters and progress for testing
"""

import sys
import requests
import json

def reset_progress():
    """Reset all checkpoint progress via API"""
    try:
        # This would connect to the dashboard if it had a reset API endpoint
        # For now, just restart the dashboard to reset everything
        print("=" * 60)
        print("RFID CHECKPOINT PROGRESS RESET")
        print("=" * 60)
        print("\nTo reset checkpoint progress:")
        print("1. Stop the dashboard (Ctrl+C)")
        print("2. Restart it using: python mine_armour_dashboard.py")
        print("\nThis will clear:")
        print("  ✓ All scan counters")
        print("  ✓ All checkpoint progress")
        print("  ✓ Debounce timers")
        print("\nThe dashboard now includes:")
        print("  ✓ 3-second debounce (prevents duplicate scans)")
        print("  ✓ Sequential checkpoint validation")
        print("  ✓ Max 4 checkpoint limit per tag")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_progress()
