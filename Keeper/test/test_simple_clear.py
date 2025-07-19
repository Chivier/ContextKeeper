#!/usr/bin/env python3
"""
Simple test to verify clear_history function
"""

import sys
import os
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the functions we need
from plugin import clear_history, DATA_DIR, context_keeper

# Create a test context
test_name = "test_delete_me"
test_path = DATA_DIR / test_name
test_path.mkdir(parents=True, exist_ok=True)

# Create a minimal context.json
context_data = {
    "contextName": test_name,
    "timestamp": "2025-01-01T00:00:00Z",
    "windows": {"applications": []},
    "browsers": []
}

with open(test_path / "context.json", "w") as f:
    json.dump(context_data, f)

print(f"Created test context at: {test_path}")
print(f"Exists: {test_path.exists()}")

# Now test clear_history
print(f"\nTesting clear_history for '{test_name}'...")

# Call clear_history with different parameter names to test flexibility
params = {"realm": test_name}  # Testing with 'realm' parameter
result = clear_history(params)

print(f"\nResult:")
print(f"  Success: {result.get('success')}")
print(f"  Message: {result.get('message', 'No message')}")

# Verify deletion
print(f"\nAfter deletion:")
print(f"  Path exists: {test_path.exists()}")

# Also test with a non-existent context
print(f"\n\nTesting with non-existent context...")
params2 = {"context_name": "this_does_not_exist"}
result2 = clear_history(params2)
print(f"Result:")
print(f"  Success: {result2.get('success')}")
print(f"  Message: {result2.get('message', 'No message')}")