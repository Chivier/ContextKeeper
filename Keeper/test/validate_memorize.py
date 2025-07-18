#!/usr/bin/env python3
"""
Validate the memorize functionality independently
"""

import json
import sys
from pathlib import Path

# Add parent directory to path (plugin.py is in parent folder)
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugin import memorize, context_keeper

def test_memorize():
    """Test memorize function directly"""
    print("Testing memorize function...")
    print("="*60)
    
    # Test 1: Missing parameters
    print("\nTest 1: Missing parameters")
    result = memorize()
    print(f"Result: {result}")
    assert result['success'] == False
    assert 'Parameters required' in result['message']
    
    # Test 2: With realm_name
    print("\nTest 2: With realm_name parameter")
    params = {"realm_name": "test_realm"}
    result = memorize(params)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 3: With context_name
    print("\nTest 3: With context_name parameter")
    params = {"context_name": "test_context"}
    result = memorize(params)
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Test 4: List contexts to verify
    print("\nTest 4: Listing saved contexts")
    contexts = context_keeper.list_contexts()
    print(f"Saved contexts: {contexts}")
    
    print("\n" + "="*60)
    print("Validation complete!")

if __name__ == "__main__":
    test_memorize()