#!/usr/bin/env python3
"""Test response format"""

import json

# Test the format
response = {"success": True, "message": "Test message with emoji 🎉"}

# This is what write_response does
json_message = json.dumps(response) + "<<END>>"

print("Correct format:")
print(json_message)
print()

# Verify the JSON part is valid
json_part = json_message.replace("<<END>>", "")
parsed = json.loads(json_part)
print("Parsed successfully:")
print(f"  Success: {parsed['success']}")
print(f"  Message: {parsed['message']}")
print()

# Show what was wrong before
wrong_response = {"success": True, "message": "Test message with emoji 🎉<<END>>"}
wrong_json_message = json.dumps(wrong_response) + "<<END>>"
print("Wrong format (what was happening):")
print(wrong_json_message)