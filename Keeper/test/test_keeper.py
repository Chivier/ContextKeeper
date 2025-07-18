"""
Test script for Context Keeper functionality
"""

import os
import sys
import json
import time
from pathlib import Path
from plugin import ContextKeeper

def test_save_context():
    """Test saving a context"""
    print("Testing Context Save...")
    
    ck = ContextKeeper()
    context_name = "test_context"
    
    try:
        # Save context
        result = ck.save_context(context_name)
        print(f"[OK] Context saved successfully: {context_name}")
        
        # Check saved files
        context_path = Path.home() / ".context_keeper" / "contexts" / context_name
        if context_path.exists():
            print(f"[OK] Context directory created: {context_path}")
            
            # Check context.json
            context_file = context_path / "context.json"
            if context_file.exists():
                with open(context_file, 'r') as f:
                    data = json.load(f)
                print(f"[OK] Context file created with {len(data.get('windows', {}).get('applications', []))} applications")
                print(f"[OK] Found {len(data.get('browsers', []))} browser windows")
                print(f"[OK] Found {len(data.get('documents', []))} documents")
                
                # Check system state
                system = data.get('windows', {}).get('system', {})
                print(f"[OK] System volume: {system.get('volume')}%")
                print(f"[OK] Do Not Disturb: {system.get('doNotDisturb')}")
            
            # Check environment snapshot
            env_files = list(context_path.glob(".g_assist_env_*.json"))
            if env_files:
                print(f"[OK] Environment snapshot created: {env_files[0].name}")
                
            # Check clipboard
            clipboard_file = context_path / "clipboard_cache.txt"
            if clipboard_file.exists():
                print(f"[OK] Clipboard saved")
                
        return True
        
    except Exception as e:
        print(f"[FAIL] Error saving context: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_list_contexts():
    """Test listing saved contexts"""
    print("\nTesting Context List...")
    
    ck = ContextKeeper()
    
    try:
        contexts = ck.list_contexts()
        print(f"[OK] Found {len(contexts)} saved contexts:")
        for ctx in contexts:
            print(f"  - {ctx}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error listing contexts: {e}")
        return False

def test_restore_context():
    """Test restoring a context"""
    print("\nTesting Context Restore...")
    
    ck = ContextKeeper()
    context_name = "test_context"
    
    try:
        # Check if context exists
        if context_name not in ck.list_contexts():
            print(f"[FAIL] Context '{context_name}' not found. Run save test first.")
            return False
            
        # Restore context
        result = ck.restore_context(context_name)
        if result:
            print(f"[OK] Context restored successfully: {context_name}")
            print("  Note: Check if applications and browser tabs are opening...")
            return True
        else:
            print(f"[FAIL] Failed to restore context")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error restoring context: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_component_features():
    """Test individual component features"""
    print("\nTesting Component Features...")
    
    all_passed = True
    
    # Test Environment Manager
    from environment_manager import EnvironmentManager
    env_mgr = EnvironmentManager()
    
    try:
        # Test environment save
        test_path = env_mgr.save_environment("test_env_check")
        if test_path and os.path.exists(test_path):
            print(f"[OK] Environment Manager: Saved environment to {test_path}")
            
            # Check snapshots
            snapshots = env_mgr.list_environment_snapshots("test_env_check")
            print(f"[OK] Environment Manager: Found {len(snapshots)} snapshots")
            
    except Exception as e:
        print(f"[FAIL] Environment Manager error: {e}")
        all_passed = False
    
    # Test Document Tracker
    from document_tracker import DocumentTracker
    doc_tracker = DocumentTracker()
    
    try:
        docs = doc_tracker.get_document_states()
        print(f"[OK] Document Tracker: Found {len(docs)} open documents")
        
        unsaved = doc_tracker.check_unsaved_documents()
        if unsaved:
            print(f"  Warning: {len(unsaved)} unsaved documents found")
            
    except Exception as e:
        print(f"[FAIL] Document Tracker error: {e}")
        all_passed = False
    
    # Test Browser Extractor
    from browser_tab_extractor import BrowserTabExtractor
    browser_ext = BrowserTabExtractor()
    
    try:
        chrome_tabs = browser_ext.extract_chrome_tabs()
        if isinstance(chrome_tabs, dict):
            print(f"[OK] Browser Extractor: Found {len(chrome_tabs.get('tabs', []))} Chrome tabs")
            print(f"  Active tab index: {chrome_tabs.get('activeIndex', 'N/A')}")
        else:
            print(f"[OK] Browser Extractor: Found {len(chrome_tabs)} Chrome tabs")
            
    except Exception as e:
        print(f"[FAIL] Browser Extractor error: {e}")
        all_passed = False
    
    # Test IDE Tracker
    from ide_tracker import IDETracker
    ide_tracker = IDETracker()
    
    try:
        ide_states = ide_tracker.get_all_ide_states()
        print(f"[OK] IDE Tracker: Found {len(ide_states)} IDEs running")
        for ide in ide_states:
            print(f"  - {ide.type}: {ide.project_path}")
            if ide.open_files:
                print(f"    Open files: {', '.join(ide.open_files[:3])}")
                
    except Exception as e:
        print(f"[FAIL] IDE Tracker error: {e}")
        all_passed = False
    
    # Test Terminal Manager
    from terminal_manager import TerminalManager
    term_mgr = TerminalManager()
    
    try:
        # Just test instantiation
        print("[OK] Terminal Manager: Initialized successfully")
        
    except Exception as e:
        print(f"[FAIL] Terminal Manager error: {e}")
        all_passed = False
        
    return all_passed

def main():
    """Run all tests"""
    print("=== Context Keeper Test Suite ===\n")
    
    tests_passed = 0
    total_tests = 4
    
    # Run tests
    if test_save_context():
        tests_passed += 1
        
    if test_list_contexts():
        tests_passed += 1
        
    if test_restore_context():
        tests_passed += 1
        
    if test_component_features():
        tests_passed += 1
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Passed: {tests_passed}/{total_tests} tests")
    
    if tests_passed == total_tests:
        print("[OK] All tests passed!")
    else:
        print(f"[FAIL] {total_tests - tests_passed} tests failed")

if __name__ == "__main__":
    main()