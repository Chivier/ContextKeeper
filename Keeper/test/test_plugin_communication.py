#!/usr/bin/env python3
"""
Test script to debug G-Assist plugin communication
Tests the plugin communication protocol directly
"""

import json
import subprocess
import sys
import time
from pathlib import Path

def test_plugin_communication():
    """Test the plugin communication with debug output"""
    
    print("Starting G-Assist Keeper Plugin Communication Test")
    print("=" * 60)
    
    # Path to the executable - look in parent directory
    exe_path = Path(__file__).parent.parent / "g-assist-plugin-keeper.exe"
    if not exe_path.exists():
        exe_path = Path(__file__).parent.parent / "dist" / "g-assist-plugin-keeper.exe"
    
    if not exe_path.exists():
        print(f"ERROR: Plugin executable not found at {exe_path}")
        print("Please run build.bat first to create the executable")
        return
    
    print(f"Found plugin executable: {exe_path}")
    
    # Start the plugin process
    try:
        process = subprocess.Popen(
            [str(exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        print("Plugin process started successfully")
    except Exception as e:
        print(f"ERROR: Failed to start plugin process: {e}")
        return
    
    # Test 1: Initialize command
    print("\nTest 1: Sending initialize command...")
    initialize_cmd = {
        "tool_calls": [{
            "func": "initialize"
        }]
    }
    
    try:
        # Send command
        cmd_str = json.dumps(initialize_cmd)
        print(f"Sending: {cmd_str}")
        process.stdin.write(cmd_str)
        process.stdin.flush()
        
        # Read response with timeout
        response = ""
        start_time = time.time()
        while time.time() - start_time < 5:  # 5 second timeout
            chunk = process.stdout.read(1)
            if not chunk:
                break
            response += chunk
            if "<<END>>" in response:
                break
        
        if response:
            print(f"Response: {response}")
        else:
            print("ERROR: No response received")
            
    except Exception as e:
        print(f"ERROR during initialize: {e}")
    
    # Test 2: Memorize command
    print("\nTest 2: Testing memorize command...")
    memorize_cmd = {
        "tool_calls": [{
            "func": "memorize",
            "params": {
                "realm_name": "test_realm"
            }
        }]
    }
    
    try:
        cmd_str = json.dumps(memorize_cmd)
        print(f"Sending: {cmd_str}")
        process.stdin.write(cmd_str)
        process.stdin.flush()
        
        # Read response with timeout
        response = ""
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 second timeout for memorize
            chunk = process.stdout.read(1)
            if not chunk:
                break
            response += chunk
            if "<<END>>" in response:
                break
        
        if response:
            print(f"Response: {response}")
        else:
            print("ERROR: No response received")
            
    except Exception as e:
        print(f"ERROR during memorize: {e}")
    
    # Test 3: List contexts
    print("\nTest 3: Testing list_contexts command...")
    list_cmd = {
        "tool_calls": [{
            "func": "list_contexts"
        }]
    }
    
    try:
        cmd_str = json.dumps(list_cmd)
        print(f"Sending: {cmd_str}")
        process.stdin.write(cmd_str)
        process.stdin.flush()
        
        # Read response
        response = ""
        start_time = time.time()
        while time.time() - start_time < 5:
            chunk = process.stdout.read(1)
            if not chunk:
                break
            response += chunk
            if "<<END>>" in response:
                break
        
        if response:
            print(f"Response: {response}")
        else:
            print("ERROR: No response received")
            
    except Exception as e:
        print(f"ERROR during list_contexts: {e}")
    
    # Shutdown
    print("\nSending shutdown command...")
    shutdown_cmd = {
        "tool_calls": [{
            "func": "shutdown"
        }]
    }
    
    try:
        cmd_str = json.dumps(shutdown_cmd)
        process.stdin.write(cmd_str)
        process.stdin.flush()
        time.sleep(1)
    except:
        pass
    
    # Check process status
    process.terminate()
    process.wait(timeout=5)
    
    print("\nTest completed.")
    print(f"Check logs at: {Path.home() / 'keeper_plugin.log'}")
    print(f"Debug logs at: {Path.home() / 'keeper_plugin_debug.log'}")

if __name__ == "__main__":
    test_plugin_communication()