"""
Simple browser tab save/restore commands
"""

from browser_tab_saver import BrowserTabSaver
import sys


def save_tabs(session_name=None):
    """Save all browser tabs to JSON."""
    saver = BrowserTabSaver()
    result = saver.save_all_tabs(session_name)
    
    if result['success']:
        print(f"[OK] Saved {result['metadata']['total_tabs']} tabs to '{result['session_name']}'")
        print(f"  Browsers: {', '.join(result['metadata']['browsers_found'])}")
    else:
        print(f"[ERROR] Failed to save tabs: {result['error']}")
        return False
    
    return True


def restore_tabs(session_name, browser=None):
    """Restore browser tabs from JSON."""
    saver = BrowserTabSaver()
    result = saver.restore_tabs(session_name, browser)
    
    if result['success']:
        print(f"[OK] Restored {result['restored_tabs']} tabs from '{session_name}'")
        if browser:
            print(f"  Browser: {browser}")
    else:
        print(f"[ERROR] Failed to restore tabs: {result['error']}")
        return False
    
    return True


def list_sessions():
    """List all saved browser tab sessions."""
    saver = BrowserTabSaver()
    sessions = saver.list_saved_sessions()
    
    if not sessions:
        print("No saved sessions found.")
        return
    
    print(f"Found {len(sessions)} saved sessions:\n")
    for i, session in enumerate(sessions, 1):
        print(f"{i}. {session['session_name']}")
        print(f"   - Saved: {session['timestamp']}")
        print(f"   - Tabs: {session['total_tabs']}")
        print(f"   - Browsers: {', '.join(session['browsers'])}")
        print()


def delete_session(session_name):
    """Delete a saved session."""
    saver = BrowserTabSaver()
    if saver.delete_session(session_name):
        print(f"[OK] Deleted session '{session_name}'")
    else:
        print(f"[ERROR] Failed to delete session '{session_name'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python browser_commands.py save [session_name]")
        print("  python browser_commands.py restore <session_name> [browser]")
        print("  python browser_commands.py list")
        print("  python browser_commands.py delete <session_name>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "save":
        session_name = sys.argv[2] if len(sys.argv) > 2 else None
        save_tabs(session_name)
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Error: session_name required for restore")
            sys.exit(1)
        session_name = sys.argv[2]
        browser = sys.argv[3] if len(sys.argv) > 3 else None
        restore_tabs(session_name, browser)
    
    elif command == "list":
        list_sessions()
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: session_name required for delete")
            sys.exit(1)
        delete_session(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)