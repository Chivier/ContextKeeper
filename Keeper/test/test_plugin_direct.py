"""
Direct test script for Context Keeper plugin
This tests the plugin functions directly without G-Assist
"""

import json
import subprocess
import time

def test_plugin_direct():
    """Test plugin by sending commands directly"""
    
    # Test commands
    test_commands = [
        {
            "name": "Initialize",
            "command": {
                "tool_calls": [{
                    "func": "initialize"
                }]
            }
        },
        {
            "name": "List Contexts",
            "command": {
                "tool_calls": [{
                    "func": "list_contexts",
                    "params": {}
                }]
            }
        },
        {
            "name": "Quick Keep",
            "command": {
                "tool_calls": [{
                    "func": "quick_keep",
                    "params": {}
                }]
            }
        },
        {
            "name": "Keep Context",
            "command": {
                "tool_calls": [{
                    "func": "keep_context",
                    "params": {
                        "context_name": "test_direct"
                    }
                }]
            }
        }
    ]
    
    print("Testing Context Keeper Plugin Directly...")
    print("=" * 50)
    
    # Start the plugin process
    plugin_path = r"dist\context-keeper\g-assist-plugin-contextkeeper.exe"
    
    try:
        # Start plugin
        process = subprocess.Popen(
            plugin_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"Plugin started with PID: {process.pid}")
        time.sleep(1)
        
        # Test each command
        for test in test_commands:
            print(f"\nTesting: {test['name']}")
            print(f"Command: {json.dumps(test['command'])}")
            
            # Send command
            command_json = json.dumps(test['command']) + '\n'
            process.stdin.write(command_json)
            process.stdin.flush()
            
            # Wait for response
            time.sleep(0.5)
            
            # Try to read response (this might not work perfectly due to pipe buffering)
            print("Waiting for response...")
            
        # Send shutdown
        print("\nSending shutdown command...")
        shutdown_command = json.dumps({
            "tool_calls": [{
                "func": "shutdown"
            }]
        }) + '\n'
        process.stdin.write(shutdown_command)
        process.stdin.flush()
        
        # Wait for process to end
        process.wait(timeout=5)
        print("\nPlugin shut down successfully")
        
    except FileNotFoundError:
        print(f"ERROR: Plugin not found at {plugin_path}")
        print("Please run build.bat first")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Test complete. Check %USERPROFILE%\\context_keeper_plugin.log for details")

if __name__ == "__main__":
    test_plugin_direct()