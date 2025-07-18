#!/usr/bin/env python3
"""
Test the memorize function directly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin import memorize, DATA_DIR

# Test memorize with a simple name
print("Testing memorize function...")

params = {"realm": "test_save"}
result = memorize(params)

print(f"\nResult:")
print(f"Success: {result.get('success')}")
print(f"Message length: {len(result.get('message', ''))}")
print(f"Message preview: {result.get('message', '')[:200]}...")

# Check if context was created
context_path = DATA_DIR / "test_save"
print(f"\nContext created: {context_path.exists()}")
if context_path.exists():
    print("Files in context directory:")
    for item in context_path.iterdir():
        print(f"  - {item.name}")