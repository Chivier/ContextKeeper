#!/usr/bin/env python3
"""Test list_contexts function"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugin import list_contexts, DATA_DIR

print(f"DATA_DIR: {DATA_DIR}")
print(f"DATA_DIR exists: {DATA_DIR.exists()}")

if DATA_DIR.exists():
    print("\nContexts in directory:")
    for item in DATA_DIR.iterdir():
        if item.is_dir():
            has_json = (item / "context.json").exists()
            print(f"  - {item.name} (has context.json: {has_json})")

print("\nTesting list_contexts function...")
start_time = time.time()

result = list_contexts()

elapsed = time.time() - start_time
print(f"\nExecution time: {elapsed:.2f} seconds")

print(f"\nResult:")
print(f"  Success: {result.get('success')}")
print(f"  Message length: {len(result.get('message', ''))}")

# Print first 500 chars of message
msg = result.get('message', '')
if len(msg) > 500:
    print(f"  Message preview: {msg[:500]}...")
else:
    print(f"  Full message: {repr(msg)}")