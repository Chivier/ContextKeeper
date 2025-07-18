#!/usr/bin/env python3
"""
Test script to debug clear_history function
Run this to test the clear_history functionality directly
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the plugin module
from plugin import clear_history, DATA_DIR, LOG_FILE

# Set up console logging for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

def test_clear_history():
    """Test the clear_history function"""
    print(f"\n=== Testing clear_history function ===")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"LOG_FILE: {LOG_FILE}")
    
    # List existing contexts
    print(f"\nExisting contexts:")
    if DATA_DIR.exists():
        for item in DATA_DIR.iterdir():
            if item.is_dir():
                print(f"  - {item.name}")
    else:
        print("  (DATA_DIR does not exist)")
    
    # Get context name to delete
    context_name = input("\nEnter context name to delete (or 'test' to create and delete a test context): ").strip()
    
    if context_name == 'test':
        # Create a test context
        test_context = DATA_DIR / "test_context_delete"
        test_context.mkdir(parents=True, exist_ok=True)
        (test_context / "context.json").write_text(json.dumps({
            "contextName": "test_context_delete",
            "timestamp": "2025-01-01T00:00:00Z"
        }))
        print(f"Created test context: {test_context}")
        context_name = "test_context_delete"
    
    # Test clear_history
    print(f"\nCalling clear_history for '{context_name}'...")
    params = {"context_name": context_name}
    
    result = clear_history(params)
    
    print(f"\nResult: {result}")
    print(f"Success: {result.get('success', False)}")
    if 'message' in result:
        print(f"Message: {result['message']}")
    
    # Verify deletion
    context_path = DATA_DIR / context_name
    print(f"\nContext path exists after deletion: {context_path.exists()}")
    
    print(f"\nCheck the log file for detailed information: {LOG_FILE}")

if __name__ == "__main__":
    test_clear_history()