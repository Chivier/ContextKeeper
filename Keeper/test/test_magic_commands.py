"""
Test script for the new magic spell API commands
"""
import json
import time
from plugin_magic import (
    memorize, recall, grimoire, snapshot, timeshift, vanish, shroud,
    generate_success_response, generate_failure_response
)

def test_command(command_name, command_func, params=None):
    """Test a single command and display results"""
    print(f"\n{'='*60}")
    print(f"Testing: {command_name}")
    print(f"{'='*60}")
    
    try:
        result = command_func(params)
        print(f"Success: {result.get('success')}")
        if 'message' in result:
            print(f"Message:\n{result['message']}")
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"{'='*60}")
    time.sleep(1)  # Small delay between tests

def main():
    print("Context Keeper Magic API Test Suite")
    print("===================================")
    
    # Test 1: Memorize a realm
    print("\n1. Testing MEMORIZE spell")
    test_command("memorize", memorize, {"realm_name": "mystical_workspace"})
    
    # Test 2: Quick snapshot
    print("\n2. Testing SNAPSHOT spell")
    test_command("snapshot", snapshot)
    
    # Test 3: List all realms
    print("\n3. Testing GRIMOIRE spell")
    test_command("grimoire", grimoire)
    
    # Test 4: Recall a realm
    print("\n4. Testing RECALL spell")
    test_command("recall", recall, {"realm_name": "mystical_workspace"})
    
    # Test 5: Timeshift to recent
    print("\n5. Testing TIMESHIFT spell")
    test_command("timeshift", timeshift)
    
    # Test 6: Shroud windows
    print("\n6. Testing SHROUD spell")
    test_command("shroud", shroud)
    
    # Test 7: Test with old parameter names (backward compatibility)
    print("\n7. Testing backward compatibility")
    test_command("memorize (old params)", memorize, {"context_name": "legacy_test"})
    
    print("\n\nTest Examples for G-Assist:")
    print("============================")
    print("Instead of saying:")
    print("  'save workspace as test' (triggers instant replay)")
    print("  'keep context as project1' (triggers instant replay)")
    print("  'capture current state' (triggers instant replay)")
    print("\nYou can now say:")
    print("  'memorize realm as test'")
    print("  'memorize mystical_workspace'")
    print("  'snapshot' (for quick save)")
    print("  'recall test' (to restore)")
    print("  'timeshift' (to go back to recent)")
    print("  'grimoire' (to see all saved realms)")
    print("  'shroud' (to minimize all)")
    print("  'vanish' (to close all)")

if __name__ == "__main__":
    main()