#!/usr/bin/env python3
"""Test script for window closing functionality"""

import logging
import time
from windows_context_manager import WindowsContextManager
from document_tracker import DocumentTracker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_window_operations():
    """Test window enumeration and closing functions"""
    manager = WindowsContextManager()
    doc_tracker = DocumentTracker()
    
    print("=== Testing Window Operations ===\n")
    
    # 1. Enumerate current windows
    print("1. Current Windows:")
    windows = manager.enum_windows()
    for window in windows[:10]:  # Show first 10 windows
        print(f"   - {window.process_name}: {window.title[:50]}...")
    print(f"   Total: {len(windows)} windows\n")
    
    # 2. Check for unsaved documents
    print("2. Checking for unsaved documents:")
    unsaved = doc_tracker.check_unsaved_documents()
    if unsaved:
        print("   WARNING: Found unsaved documents:")
        for doc in unsaved:
            print(f"   - {doc['application']}: {doc['title']}")
    else:
        print("   No unsaved documents found.")
    print()
    
    # 3. Test minimize function
    print("3. Testing minimize_all_windows():")
    response = input("   Do you want to minimize all windows? (y/n): ")
    if response.lower() == 'y':
        count = manager.minimize_all_windows()
        print(f"   Minimized {count} windows.")
        time.sleep(2)
    print()
    
    # 4. Test close function (dry run)
    print("4. Testing close_all_windows() - DRY RUN:")
    print("   This will show what would be closed without actually closing anything.")
    
    # Get counts without actually closing
    windows = manager.enum_windows()
    exclude_list = [
        'explorer.exe', 'dwm.exe', 'taskmgr.exe', 'systemsettings.exe',
        'shellexperiencehost.exe', 'searchui.exe', 'cortana.exe',
        'runtimebroker.exe', 'python.exe', 'pythonw.exe', 'g-assist-plugin-python.exe'
    ]
    
    would_close = []
    would_exclude = []
    
    for window in windows:
        if window.process_name.lower() in [e.lower() for e in exclude_list]:
            would_exclude.append(window)
        elif not window.is_minimized:
            would_close.append(window)
    
    print(f"   Would close: {len(would_close)} windows")
    print(f"   Would exclude: {len(would_exclude)} system processes")
    print(f"   Already minimized: {len([w for w in windows if w.is_minimized])} windows")
    
    print("\n   Sample of windows that would be closed:")
    for window in would_close[:5]:
        print(f"   - {window.process_name}: {window.title[:50]}...")
    
    print("\n   Sample of excluded system processes:")
    for window in would_exclude[:5]:
        print(f"   - {window.process_name}: {window.title[:50]}...")
    
    # 5. Actual close test (optional)
    print("\n5. Actual close test:")
    response = input("   Do you want to actually test closing windows? (y/n): ")
    if response.lower() == 'y':
        print("   WARNING: This will close all non-system windows!")
        confirm = input("   Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            counts = manager.close_all_windows(force=False)
            print(f"\n   Results:")
            print(f"   - Closed: {counts['closed']} windows")
            print(f"   - Failed: {counts['failed']} windows")
            print(f"   - Excluded: {counts['excluded']} system processes")
        else:
            print("   Test cancelled.")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_window_operations()