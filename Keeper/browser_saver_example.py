"""
Simple example of using the browser tab saver
"""

from browser_tab_saver import BrowserTabSaver

# Create a browser tab saver instance
saver = BrowserTabSaver()

# Example 1: Save all browser tabs with a custom name
print("Saving all browser tabs...")
result = saver.save_all_tabs("my_work_session")
if result['success']:
    print(f"Successfully saved {result['metadata']['total_tabs']} tabs!")
    print(f"Session name: {result['session_name']}")
    print(f"Location: {result['save_path']}")
else:
    print(f"Failed to save: {result['error']}")

# Example 2: List all saved sessions
print("\nListing saved sessions:")
sessions = saver.list_saved_sessions()
for session in sessions:
    print(f"- {session['session_name']} ({session['total_tabs']} tabs)")

# Example 3: Restore tabs from a session
# Uncomment the lines below to restore tabs
# print("\nRestoring tabs from 'my_work_session'...")
# restore_result = saver.restore_tabs("my_work_session")
# if restore_result['success']:
#     print(f"Restored {restore_result['restored_tabs']} tabs!")

# Example 4: Save with auto-generated name
print("\nQuick save with auto-generated name:")
quick_result = saver.save_all_tabs()  # No name provided
if quick_result['success']:
    print(f"Saved as: {quick_result['session_name']}")