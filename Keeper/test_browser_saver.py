"""
Test script for the new browser tab saver functionality
"""

import logging
from browser_tab_saver import BrowserTabSaver

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=== Browser Tab Saver Test ===\n")
    
    # Create saver instance
    saver = BrowserTabSaver()
    
    # Test 1: Save all browser tabs
    print("1. Saving all browser tabs...")
    result = saver.save_all_tabs("test_session")
    if result['success']:
        print(f"   [OK] Saved successfully!")
        print(f"   - Session: {result['session_name']}")
        print(f"   - Total tabs: {result['metadata']['total_tabs']}")
        print(f"   - Browsers: {', '.join(result['metadata']['browsers_found'])}")
        print(f"   - Saved to: {result['save_path']}")
    else:
        print(f"   [ERROR] Failed: {result['error']}")
    
    # Test 2: List saved sessions
    print("\n2. Listing saved sessions...")
    sessions = saver.list_saved_sessions()
    print(f"   Found {len(sessions)} saved sessions:")
    for session in sessions[:3]:  # Show first 3
        print(f"   - {session['session_name']} ({session['total_tabs']} tabs) - {session['timestamp']}")
    
    # Test 3: Get session details
    if sessions:
        print(f"\n3. Getting details for session '{sessions[0]['session_name']}'...")
        details = saver.get_session_details(sessions[0]['session_name'])
        if details:
            print(f"   - Timestamp: {details['timestamp']}")
            print(f"   - Browsers saved:")
            for browser, data in details['browsers'].items():
                if isinstance(data, dict) and 'tabs' in data:
                    tab_count = len(data['tabs'])
                else:
                    tab_count = len(data) if isinstance(data, list) else 0
                print(f"     • {browser}: {tab_count} tabs")
    
    # Test 4: Restore tabs (user prompt)
    print("\n4. Tab restoration")
    print("   To restore tabs, run:")
    print("   >>> saver.restore_tabs('test_session')")
    print("   This will open all saved tabs in their respective browsers")
    
    # Test 5: Quick save with auto-generated name
    print("\n5. Quick save with auto-generated name...")
    quick_result = saver.save_all_tabs()
    if quick_result['success']:
        print(f"   [OK] Quick saved as: {quick_result['session_name']}")
    
    print("\n=== Test Complete ===")
    print("\nAvailable methods:")
    print("- save_all_tabs(session_name=None) - Save all browser tabs")
    print("- restore_tabs(session_name, browser=None) - Restore saved tabs")
    print("- list_saved_sessions() - List all saved sessions")
    print("- get_session_details(session_name) - Get session details")
    print("- delete_session(session_name) - Delete a saved session")

if __name__ == "__main__":
    main()