"""
Demo script showing how to use Context Keeper
"""

import time
from plugin import ContextKeeper

def main():
    print("=== Context Keeper Demo ===\n")
    
    ck = ContextKeeper()
    
    # 1. Save current context
    print("1. Saving current context...")
    context_name = "my_work_session"
    try:
        result = ck.save_context(context_name)
        print(f"   Context '{context_name}' saved successfully!")
        print(f"   - Applications: {len(result.get('windows', {}).get('applications', []))}")
        print(f"   - Browsers: {len(result.get('browsers', []))}")
        print(f"   - Documents: {len(result.get('documents', []))}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. List saved contexts
    print("\n2. Listing saved contexts...")
    contexts = ck.list_contexts()
    print(f"   Found {len(contexts)} saved contexts:")
    for ctx in contexts:
        print(f"   - {ctx}")
    
    # 3. Quick save
    print("\n3. Performing quick save...")
    from plugin import quick_save
    response = quick_save()
    if response.get('success'):
        print(f"   {response.get('message')}")
    
    # 4. List contexts again
    print("\n4. Listing contexts after quick save...")
    contexts = ck.list_contexts()
    print(f"   Found {len(contexts)} saved contexts:")
    for ctx in contexts[-3:]:  # Show last 3
        print(f"   - {ctx}")
    
    # 5. Clear windows (minimize all)
    print("\n5. Clear windows demo (will minimize all windows)...")
    print("   Press Enter to minimize all windows...")
    input()
    from plugin import clear_windows
    response = clear_windows()
    if response.get('success'):
        print(f"   {response.get('message')}")
    
    # 6. Restore context
    print(f"\n6. Restoring context '{context_name}'...")
    print("   Press Enter to restore...")
    input()
    try:
        result = ck.restore_context(context_name)
        if result:
            print(f"   Context '{context_name}' restored successfully!")
            print("   Check your desktop - windows should be restored")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n=== Demo Complete ===")
    print("Features demonstrated:")
    print("- Save context with all open windows and browser tabs")
    print("- List saved contexts")
    print("- Quick save with auto-generated name")
    print("- Clear windows (minimize all)")
    print("- Restore context with windows and applications")
    
    print("\nAdditional features available:")
    print("- Document tracking (Office, Notion, Obsidian)")
    print("- IDE state tracking (VSCode, JetBrains, etc.)")
    print("- Terminal state with environment variables")
    print("- System state (volume, clipboard, etc.)")

if __name__ == "__main__":
    main()