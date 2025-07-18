import json
import logging
import os
from ctypes import byref, windll, wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import traceback

import psutil
import pygetwindow as gw
import pyperclip

# Import our components
from environment_manager import EnvironmentManager
from windows_context_manager import WindowsContextManager, WindowInfo
from browser_tab_extractor import BrowserTabExtractor
from terminal_manager import TerminalManager
from ide_tracker import IDETracker
from document_tracker import DocumentTracker

type Response = dict[bool, Optional[str]]
DATA_DIR = Path.home() / ".keeper" / "contexts"

LOG_FILE = Path.home() / "keeper_plugin.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

INDEX_FILE = Path.home() / ".keeper" / "index.json"


class ContextKeeper:
    """Main context keeper implementation using all components"""
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.windows_manager = WindowsContextManager()
        self.browser_extractor = BrowserTabExtractor()
        self.terminal_manager = TerminalManager()
        self.ide_tracker = IDETracker()
        self.document_tracker = DocumentTracker()
        self.logger = logging.getLogger(__name__)
        
    def keep_context(self, context_name: str) -> Dict:
        """Keep complete context as per DESIGN.md"""
        context_data = {
            "contextName": context_name,
            "timestamp": datetime.now().isoformat() + "Z",
            "windows": {
                "system": {},
                "applications": [],
            },
            "browsers": [],
            "environmentVariables": {},
            "environmentSnapshot": None
        }
        
        try:
            # Check for unsaved documents first
            unsaved_docs = self.document_tracker.check_unsaved_documents()
            if unsaved_docs:
                self.logger.warning(f"Found {len(unsaved_docs)} unsaved documents")
                # In a real implementation, this would prompt the user
                
            # Save system state
            context_data["windows"]["system"] = self._save_system_state()
            
            # Keep environment variables with timestamp
            env_path = self.env_manager.keep_environment(context_name)
            context_data["environmentSnapshot"] = env_path
            
            # Get current environment for immediate reference
            context_data["environmentVariables"] = dict(os.environ)
            
            # Save clipboard
            self._save_clipboard(context_name)
            
            # Get document states
            document_states = self.document_tracker.get_document_states()
            context_data["documents"] = document_states
            
            # Get all windows
            windows = self.windows_manager.enum_windows()
            
            # Process windows by type
            for window in windows:
                self._process_window(window, context_data)
            
            # Save the main context file
            context_path = DATA_DIR / context_name
            context_path.mkdir(parents=True, exist_ok=True)
            
            with open(context_path / "context.json", "w", encoding="utf-8") as f:
                json.dump(context_data, f, indent=2)
                
            # Clean up old environment snapshots
            self.env_manager.cleanup_old_snapshots(context_name, keep_last=10)
            
            self.logger.info(f"Context '{context_name}' kept successfully")
            return context_data
            
        except Exception as e:
            self.logger.error(f"Error saving context: {e}\n{traceback.format_exc()}")
            raise
    
    def _save_system_state(self) -> Dict:
        """Keep system-level state"""
        system_state = {
            "volume": self._get_system_volume(),
            "doNotDisturb": self._get_do_not_disturb_status(),
            "clipboard": "clipboard_cache.txt"
        }
        return system_state
    
    def _get_system_volume(self) -> int:
        """Get system volume level"""
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            # Get default audio device
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            
            # Get volume level (0.0 to 1.0)
            current_volume = volume.GetMasterVolumeLevelScalar()
            return int(current_volume * 100)
        except Exception as e:
            self.logger.warning(f"Could not get system volume: {e}")
            return 50  # Default placeholder
    
    def _get_do_not_disturb_status(self) -> bool:
        """Get Windows Do Not Disturb (Focus Assist) status"""
        try:
            import winreg
            
            # Check Windows Focus Assist registry key
            key_path = r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\Cache\DefaultAccount\$$windows.data.notifications.quiethourssettings\Current\Data"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                data, _ = winreg.QueryValueEx(key, "Data")
                # Check if Focus Assist is enabled (simplified check)
                return len(data) > 0 and data[0] != 0
        except Exception as e:
            self.logger.warning(f"Could not get DND status: {e}")
            return False
    
    def _get_window_virtual_desktop(self, hwnd: int) -> int:
        """Get virtual desktop ID for a window"""
        try:
            import ctypes
            from ctypes import wintypes, POINTER
            from comtypes import GUID, IUnknown, COMMETHOD, HRESULT
            
            # Try to use Windows Virtual Desktop API
            # This is a simplified version - full implementation would need COM interfaces
            return 1  # Default to desktop 1 for now
        except Exception as e:
            self.logger.warning(f"Could not get virtual desktop: {e}")
            return 1
    
    def _detect_browser_profile(self, window: WindowInfo) -> str:
        """Detect browser profile from window title or process"""
        try:
            # Check window title for profile indicators
            title = window.title.lower()
            
            # Common profile patterns in window titles
            if '- profile' in title:
                # Extract profile name from title
                parts = title.split('- profile')
                if len(parts) > 1:
                    profile_part = parts[1].strip()
                    profile_name = profile_part.split('-')[0].strip()
                    return profile_name
            
            # Check for user indicators
            if 'personal' in title:
                return 'Personal'
            elif 'work' in title:
                return 'Work'
            
            return 'Default'
        except Exception as e:
            self.logger.warning(f"Could not detect browser profile: {e}")
            return 'Default'
    
    def _save_clipboard(self, context_name: str):
        """Keep clipboard content"""
        try:
            clipboard_data = pyperclip.paste()
            clipboard_path = DATA_DIR / context_name / "clipboard_cache.txt"
            clipboard_path.parent.mkdir(parents=True, exist_ok=True)
            clipboard_path.write_text(clipboard_data, encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Failed to capture clipboard: {e}")
    
    def _process_window(self, window: WindowInfo, context_data: Dict):
        """Process a window and add to appropriate category"""
        process_name = window.process_name.lower()
        
        # Check if it's a browser
        if any(browser in process_name for browser in ['chrome', 'firefox', 'edge', 'msedge']):
            self._process_browser_window(window, context_data)
        # Check if it's a terminal
        elif any(term in process_name for term in ['terminal', 'cmd', 'powershell', 'pwsh', 'termius']):
            self._process_terminal_window(window, context_data)
        # Check if it's an IDE
        elif any(ide in process_name for ide in ['code', 'cursor', 'pycharm', 'idea', 'sublime', 'notepad++']):
            self._process_ide_window(window, context_data)
        # Other applications
        else:
            self._process_application_window(window, context_data)
    
    def _process_browser_window(self, window: WindowInfo, context_data: Dict):
        """Process browser window"""
        browser_type = 'chrome'
        if 'firefox' in window.process_name.lower():
            browser_type = 'firefox'
        elif 'edge' in window.process_name.lower():
            browser_type = 'edge'
            
        # Get tabs
        tabs_result = []
        active_index = 0
        
        if browser_type == 'chrome':
            result = self.browser_extractor.extract_chrome_tabs()
        elif browser_type == 'edge':
            result = self.browser_extractor.extract_edge_tabs()
        elif browser_type == 'firefox':
            result = self.browser_extractor.extract_firefox_tabs()
        else:
            result = []
            
        # Handle new format with active index
        if isinstance(result, dict) and 'tabs' in result:
            tabs_result = result['tabs']
            active_index = result.get('activeIndex', 0)
        else:
            tabs_result = result if isinstance(result, list) else []
            
        browser_data = {
            "type": browser_type,
            "processName": window.process_name,
            "profile": self._detect_browser_profile(window),
            "tabs": tabs_result,
            "activeTabIndex": active_index,
            "window": {
                "x": window.x,
                "y": window.y,
                "width": window.width,
                "height": window.height,
                "state": "maximized" if window.is_maximized else "normal",
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd)
            }
        }
        
        context_data["browsers"].append(browser_data)
    
    def _process_terminal_window(self, window: WindowInfo, context_data: Dict):
        """Process terminal window"""
        terminal_info = self.terminal_manager.get_terminal_info(
            window.process_name, 
            window.hwnd
        )
        
        app_data = {
            "type": terminal_info['type'],
            "processName": window.process_name,
            "tabs": terminal_info['tabs'],
            "window": {
                "x": window.x,
                "y": window.y,
                "width": window.width,
                "height": window.height,
                "state": "maximized" if window.is_maximized else "normal",
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd)
            }
        }
        
        context_data["windows"]["applications"].append(app_data)
    
    def _process_ide_window(self, window: WindowInfo, context_data: Dict):
        """Process IDE window"""
        # Get IDE states
        ide_states = self.ide_tracker.get_all_ide_states()
        
        # Find matching IDE state
        ide_state = None
        for state in ide_states:
            if state.process_name.lower() == window.process_name.lower():
                ide_state = state
                break
                
        if ide_state:
            app_data = {
                "type": ide_state.type,
                "processName": window.process_name,
                "projectPath": ide_state.project_path,
                "openFiles": ide_state.open_files,
                "window": {
                    "x": window.x,
                    "y": window.y,
                    "width": window.width,
                    "height": window.height,
                    "state": "maximized" if window.is_maximized else "normal",
                    "virtualDesktop": 1  # Would need virtual desktop detection
                }
            }
            
            context_data["windows"]["applications"].append(app_data)
    
    def _process_application_window(self, window: WindowInfo, context_data: Dict):
        """Process generic application window"""
        app_data = {
            "type": "application",
            "processName": window.process_name,
            "title": window.title,
            "window": {
                "x": window.x,
                "y": window.y,
                "width": window.width,
                "height": window.height,
                "state": "maximized" if window.is_maximized else "normal",
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd)
            }
        }
        
        context_data["windows"]["applications"].append(app_data)
    
    def restore_context(self, context_name: str) -> bool:
        """Restore a saved context"""
        try:
            context_path = DATA_DIR / context_name
            if not context_path.exists():
                self.logger.error(f"Context '{context_name}' not found")
                return False
                
            # Load context data
            with open(context_path / "context.json", "r", encoding="utf-8") as f:
                context_data = json.load(f)
                
            # Restore environment variables
            try:
                self.env_manager.restore_environment(context_name)
            except Exception as e:
                self.logger.warning(f"Failed to restore environment: {e}")
                
            # Restore clipboard
            try:
                clipboard_file = context_path / "clipboard_cache.txt"
                if clipboard_file.exists():
                    clipboard_data = clipboard_file.read_text(encoding="utf-8")
                    pyperclip.copy(clipboard_data)
            except Exception as e:
                self.logger.warning(f"Failed to restore clipboard: {e}")
                
            # Restore documents
            for doc in context_data.get("documents", []):
                try:
                    self.document_tracker.restore_document(doc)
                except Exception as e:
                    self.logger.warning(f"Failed to restore document: {e}")
                    
            # Restore applications
            for app in context_data.get("windows", {}).get("applications", []):
                self._restore_application(app)
                
            # Restore browsers
            for browser in context_data.get("browsers", []):
                self._restore_browser(browser)
                
            # Restore window positions for existing windows
            self._restore_window_positions(context_data)
            
            self.logger.info(f"Context '{context_name}' restored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring context: {e}\n{traceback.format_exc()}")
            return False
    
    def _restore_application(self, app_data: Dict):
        """Restore an application"""
        app_type = app_data.get("type")
        
        if app_type in ["vscode", "pycharm", "intellij_idea", "sublime_text"]:
            # Restore IDE
            from ide_tracker import IDEState
            ide_state = IDEState(
                type=app_type,
                process_name=app_data.get("processName"),
                project_path=app_data.get("projectPath"),
                open_files=app_data.get("openFiles", []),
                window_title="",
                recent_projects=[]
            )
            self.ide_tracker.restore_ide_state(ide_state)
            
        elif app_type in ["windows_terminal", "cmd", "powershell"]:
            # Restore terminal
            self.terminal_manager.restore_terminal_tabs([app_data])
    
    def _restore_browser(self, browser_data: Dict):
        """Restore browser tabs"""
        browser_type = browser_data.get("type")
        tabs = browser_data.get("tabs", [])
        
        if not tabs:
            return
            
        # Build URL list
        urls = [tab.get("url") for tab in tabs if tab.get("url")]
        
        if browser_type == "chrome":
            os.system(f'start chrome {" ".join(urls)}')
        elif browser_type == "edge":
            os.system(f'start msedge {" ".join(urls)}')
        elif browser_type == "firefox":
            os.system(f'start firefox {" ".join(urls)}')
    
    def _restore_window_positions(self, context_data: Dict):
        """Restore window positions for existing windows"""
        current_windows = self.windows_manager.enum_windows()
        
        # Create a mapping of process names to saved window data
        saved_windows = {}
        
        # Add applications
        for app in context_data.get("windows", {}).get("applications", []):
            process_name = app.get("processName", "").lower()
            saved_windows[process_name] = app.get("window", {})
            
        # Add browsers
        for browser in context_data.get("browsers", []):
            process_name = browser.get("processName", "").lower()
            saved_windows[process_name] = browser.get("window", {})
            
        # Restore positions
        for window in current_windows:
            process_name = window.process_name.lower()
            if process_name in saved_windows:
                saved_pos = saved_windows[process_name]
                self.windows_manager.restore_window_position(
                    window.hwnd,
                    saved_pos.get("x", window.x),
                    saved_pos.get("y", window.y),
                    saved_pos.get("width", window.width),
                    saved_pos.get("height", window.height),
                    saved_pos.get("state") == "maximized",
                    saved_pos.get("state") == "minimized"
                )
    
    def list_contexts(self) -> List[str]:
        """List all saved contexts"""
        contexts = []
        
        if DATA_DIR.exists():
            for context_dir in DATA_DIR.iterdir():
                if context_dir.is_dir() and (context_dir / "context.json").exists():
                    contexts.append(context_dir.name)
                    
        return sorted(contexts)


# Global instance
context_keeper = ContextKeeper()


def log_context(context_name: str):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    index = []
    if INDEX_FILE.exists():
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except:
            index = []
    if context_name in index:
        index.remove(context_name)
    index.insert(0, context_name)
    index = index[:10]  # keep recent 10
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def quick_keep(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    context_name = "auto-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Keep the context and get detailed data
        context_data = context_keeper.keep_context(context_name)
        log_context(context_name)
        
        # Count items for summary
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        total_tabs = sum(len(b.get("tabs", [])) for b in context_data.get("browsers", []))
        
        message = f"Quick keep SUCCESSFUL!\n"
        message += f"Saved as: {context_name}\n"
        message += f"Windows: {windows_count}\n"
        message += f"Browser tabs: {total_tabs}\n"
        message += "Use 'Quick switch' to restore instantly!"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Quick keep failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"Quick keep failed: {str(e)}")


def quick_switch(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    if not INDEX_FILE.exists():
        return generate_failure_response("No recent contexts available.")
    
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except:
        return generate_failure_response("Index file corrupted.")

    if not index:
        return generate_failure_response("Context list is empty.")
    
    # Show recent contexts list
    message = "Recent contexts:\n"
    for i, ctx in enumerate(index[:5], 1):
        message += f"{i}. {ctx}\n"
    
    message += f"\nSwitching to: {index[0]}\n"
    
    # Restore most recent context
    context_name = index[0]
    return restore_context({"context_name": context_name}, context, system_info)


def list_contexts(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """List all saved contexts with details"""
    try:
        contexts = context_keeper.list_contexts()
        
        if not contexts:
            return generate_success_response("No saved contexts found.")
        
        message = f"Found {len(contexts)} saved contexts:\n\n"
        
        for ctx_name in contexts[:20]:  # Show max 20
            try:
                context_path = DATA_DIR / ctx_name / "context.json"
                with open(context_path, "r", encoding="utf-8") as f:
                    ctx_data = json.load(f)
                
                # Get stats
                windows_count = len(ctx_data.get("windows", {}).get("applications", []))
                browsers_count = len(ctx_data.get("browsers", []))
                total_tabs = sum(len(b.get("tabs", [])) for b in ctx_data.get("browsers", []))
                timestamp = ctx_data.get("timestamp", "Unknown")
                
                message += f"{ctx_name}:\n"
                message += f"  Saved: {timestamp}\n"
                message += f"  Windows: {windows_count}, Tabs: {total_tabs}\n\n"
                
            except Exception as e:
                message += f"{ctx_name}: (Error reading)\n\n"
        
        if len(contexts) > 20:
            message += f"...and {len(contexts) - 20} more contexts"
        
        return generate_success_response(message.rstrip())
        
    except Exception as e:
        logging.error(f"List contexts failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"Failed to list contexts: {str(e)}")


def clear_windows(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    temp_name = "autokeep-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Check for unsaved documents before closing
        unsaved_docs = context_keeper.document_tracker.check_unsaved_documents()
        if unsaved_docs:
            doc_list = "\n".join([f"- {doc['application']}: {doc['title']}" for doc in unsaved_docs])
            logging.warning(f"Found {len(unsaved_docs)} unsaved documents:\n{doc_list}")
            # In a real implementation, this would prompt the user
        
        # Keep context first
        context_keeper.keep_context(temp_name)
        log_context(temp_name)
        
        # Close all windows (excluding system processes)
        counts = context_keeper.windows_manager.close_all_windows(force=False)
        
        return generate_success_response(
            f"Context kept as '{temp_name}'. "
            f"Closed: {counts['closed']} windows, "
            f"Failed: {counts['failed']}, "
            f"Excluded: {counts['excluded']} system processes."
        )
    except Exception as e:
        return generate_failure_response(f"Clear windows failed: {str(e)}")


def minimize_windows(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Safer alternative that just minimizes windows instead of closing them"""
    temp_name = "autokeep-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        context_keeper.keep_context(temp_name)
        log_context(temp_name)
        
        # Minimize all windows
        count = context_keeper.windows_manager.minimize_all_windows()
        
        return generate_success_response(f"Context kept as '{temp_name}' and {count} windows minimized.")
    except Exception as e:
        return generate_failure_response(f"Minimize windows failed: {str(e)}")


# ======================================
# MAGIC SPELL COMMANDS (NEW API)
# ======================================

def memorize(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Magic spell to memorize current realm (workspace)"""
    if not params:
        return generate_failure_response("Parameters required.")
    # Support both old and new parameter names
    realm_name = params.get("realm_name") or params.get("context_name", "unnamed")
    
    try:
        # Keep the context and get detailed data
        context_data = context_keeper.keep_context(realm_name)
        log_context(realm_name)
        
        # Extract statistics from the saved context
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        
        # Count browser tabs
        total_tabs = 0
        for browser in context_data.get("browsers", []):
            total_tabs += len(browser.get("tabs", []))
        
        # Count IDE files
        total_files = 0
        for app in context_data.get("windows", {}).get("applications", []):
            if app.get("type") in ["vscode", "cursor", "pycharm", "intellij_idea"]:
                total_files += len(app.get("openFiles", []))
        
        # Count terminal tabs
        terminal_tabs = 0
        for app in context_data.get("windows", {}).get("applications", []):
            if app.get("type") in ["windows_terminal", "cmd", "powershell"]:
                terminal_tabs += len(app.get("tabs", []))
        
        # Count environment variables
        env_vars_count = len(context_data.get("environmentVariables", {}))
        
        # Build detailed response message with magic theme
        message = f"✨ Realm '{realm_name}' has been MEMORIZED! ✨\n"
        message += f"📚 Windows preserved: {windows_count}\n"
        message += f"🌐 Browser portals: {total_tabs}\n"
        if total_files > 0:
            message += f"📜 Sacred scrolls (IDE files): {total_files}\n"
        if terminal_tabs > 0:
            message += f"🔮 Terminal crystals: {terminal_tabs}\n"
        message += f"🗝️ Enchanted variables: {env_vars_count}"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Memorize spell failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"🚫 The memorize spell failed for realm '{realm_name}': {str(e)}")


def recall(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Summon a previously memorized realm"""
    if not params:
        return generate_failure_response("Parameters required.")
    # Support both old and new parameter names  
    realm_name = params.get("realm_name") or params.get("context_name", "")
    if not realm_name:
        return generate_failure_response("Realm name required.")
        
    try:
        # Check if context exists
        context_path = DATA_DIR / realm_name / "context.json"
        if not context_path.exists():
            return generate_failure_response(f"🚫 Realm '{realm_name}' not found in the ethereal plane.")
        
        # Load context data to show what will be restored
        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
        
        # Count items
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        total_tabs = sum(len(b.get("tabs", [])) for b in context_data.get("browsers", []))
        
        # Perform the restoration
        success = context_keeper.restore_context(realm_name)
        
        if success:
            message = f"✨ Realm '{realm_name}' has been SUMMONED! ✨\n"
            message += f"🪟 Windows conjured: {windows_count}\n"
            message += f"🌐 Browser portals opened: {total_tabs}\n"
            message += f"🗝️ Enchanted variables: Restored\n"
            message += f"📅 Originally cast at: {context_data.get('timestamp', 'Unknown')}"
            return generate_success_response(message)
        else:
            return generate_failure_response(f"🚫 Failed to summon realm '{realm_name}' from the ethereal plane.")
            
    except Exception as e:
        logging.error(f"Recall spell failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"🚫 The recall spell failed for realm '{realm_name}': {str(e)}")


def grimoire(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Consult the mystical grimoire of saved realms"""
    try:
        contexts = context_keeper.list_contexts()
        
        if not contexts:
            return generate_success_response("📖 The grimoire is empty - no realms have been memorized yet.")
        
        message = f"📖 The Grimoire reveals {len(contexts)} memorized realms:\n\n"
        
        for ctx_name in contexts[:20]:  # Show max 20
            try:
                context_path = DATA_DIR / ctx_name / "context.json"
                with open(context_path, "r", encoding="utf-8") as f:
                    ctx_data = json.load(f)
                
                # Get stats
                windows_count = len(ctx_data.get("windows", {}).get("applications", []))
                browsers_count = len(ctx_data.get("browsers", []))
                total_tabs = sum(len(b.get("tabs", [])) for b in ctx_data.get("browsers", []))
                timestamp = ctx_data.get("timestamp", "Unknown")
                
                message += f"✨ {ctx_name}:\n"
                message += f"  📅 Cast on: {timestamp}\n"
                message += f"  🪟 Windows: {windows_count}, 🌐 Portals: {total_tabs}\n\n"
                
            except Exception as e:
                message += f"❌ {ctx_name}: (Corrupted spell)\n\n"
        
        if len(contexts) > 20:
            message += f"...and {len(contexts) - 20} more ancient realms..."
        
        return generate_success_response(message.rstrip())
        
    except Exception as e:
        logging.error(f"Grimoire consultation failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"🚫 Failed to consult the grimoire: {str(e)}")


def snapshot(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Instantly crystallize the current realm"""
    realm_name = "crystal-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Keep the context and get detailed data
        context_data = context_keeper.keep_context(realm_name)
        log_context(realm_name)
        
        # Count items for summary
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        total_tabs = sum(len(b.get("tabs", [])) for b in context_data.get("browsers", []))
        
        message = f"💎 Realm CRYSTALLIZED instantly!\n"
        message += f"✨ Preserved as: {realm_name}\n"
        message += f"🪟 Windows: {windows_count}\n"
        message += f"🌐 Browser portals: {total_tabs}\n"
        message += "⚡ Use 'timeshift' to return instantly!"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Snapshot spell failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"🚫 The snapshot spell failed: {str(e)}")


def timeshift(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Warp through the temporal vortex to the most recent realm"""
    if not INDEX_FILE.exists():
        return generate_failure_response("🚫 No temporal anchors found in the vortex.")
    
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except:
        return generate_failure_response("🚫 The temporal index is corrupted.")

    if not index:
        return generate_failure_response("🚫 The temporal vortex is empty.")
    
    # Show recent contexts list
    message = "🌀 Recent temporal anchors:\n"
    for i, ctx in enumerate(index[:5], 1):
        message += f"{i}. {ctx}\n"
    
    message += f"\n⚡ Warping to: {index[0]}\n"
    
    # Restore most recent context
    realm_name = index[0]
    return recall({"realm_name": realm_name}, context, system_info)


def vanish(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Cast a vanishing spell on all windows"""
    temp_name = "vanished-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Check for unsaved documents before closing
        unsaved_docs = context_keeper.document_tracker.check_unsaved_documents()
        if unsaved_docs:
            doc_list = "\n".join([f"- {doc['application']}: {doc['title']}" for doc in unsaved_docs])
            logging.warning(f"Found {len(unsaved_docs)} unsaved documents:\n{doc_list}")
        
        # Keep context first
        context_keeper.keep_context(temp_name)
        log_context(temp_name)
        
        # Close all windows (excluding system processes)
        counts = context_keeper.windows_manager.close_all_windows(force=False)
        
        return generate_success_response(
            f"🌫️ VANISH spell cast successfully!\n"
            f"✨ Realm preserved as '{temp_name}'\n"
            f"💨 Vanished: {counts['closed']} windows\n"
            f"❌ Resisted: {counts['failed']}\n"
            f"🛡️ Protected: {counts['excluded']} system spirits"
        )
    except Exception as e:
        return generate_failure_response(f"🚫 Vanish spell failed: {str(e)}")


def shroud(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Cast a shrouding veil to conceal all windows"""
    temp_name = "shrouded-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        context_keeper.keep_context(temp_name)
        log_context(temp_name)
        
        # Minimize all windows
        count = context_keeper.windows_manager.minimize_all_windows()
        
        return generate_success_response(
            f"🌑 SHROUD spell cast successfully!\n"
            f"✨ Realm preserved as '{temp_name}'\n"
            f"🫥 {count} windows concealed in shadow"
        )
    except Exception as e:
        return generate_failure_response(f"🚫 Shroud spell failed: {str(e)}")


# Keep original function names for backwards compatibility
def keep_context(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    return memorize(params, context, system_info)


def restore_context(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    return recall(params, context, system_info)


def read_command() -> dict | None:
    try:
        STD_INPUT_HANDLE = -10
        pipe = windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
        chunks = []

        while True:
            BUFFER_SIZE = 4096
            message_bytes = wintypes.DWORD()
            buffer = bytes(BUFFER_SIZE)
            success = windll.kernel32.ReadFile(
                pipe, buffer, BUFFER_SIZE, byref(message_bytes), None
            )
            if not success:
                return None
            chunk = buffer.decode("utf-8")[: message_bytes.value]
            chunks.append(chunk)
            if message_bytes.value < BUFFER_SIZE:
                break

        return json.loads("".join(chunks))
    except:
        return None


def write_response(response: Response) -> None:
    try:
        STD_OUTPUT_HANDLE = -11
        pipe = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        json_message = json.dumps(response)
        message_bytes = json_message.encode("utf-8")
        message_len = len(message_bytes)
        windll.kernel32.WriteFile(
            pipe, message_bytes, message_len, wintypes.DWORD(), None
        )
    except Exception as e:
        logging.error(f"write error: {e}")


def generate_success_response(message: str = None) -> Response:
    resp = {"success": True}
    if message:
        resp["message"] = message
    return resp


def generate_failure_response(message: str = None) -> Response:
    resp = {"success": False}
    if message:
        resp["message"] = message
    return resp


def execute_initialize_command():
    return generate_success_response("Plugin initialized")


def execute_shutdown_command():
    return generate_success_response("Plugin shutdown")


# === Plugin Loop ===


def main():
    TOOL_CALLS_PROPERTY = 'tool_calls'
    CONTEXT_PROPERTY = 'messages'
    SYSTEM_INFO_PROPERTY = 'system_info'
    FUNCTION_PROPERTY = 'func'
    PARAMS_PROPERTY = 'params'
    INITIALIZE_COMMAND = 'initialize'
    SHUTDOWN_COMMAND = 'shutdown'
    
    commands = {
        'initialize': execute_initialize_command,
        'shutdown': execute_shutdown_command,
        # Original commands (for backward compatibility)
        'keep_context': keep_context,
        'restore_context': restore_context,
        'list_contexts': list_contexts,
        'quick_keep': quick_keep,
        'quick_switch': quick_switch,
        'clear_windows': clear_windows,
        'minimize_windows': minimize_windows,
        # New magic commands
        'memorize': memorize,
        'recall': recall,
        'grimoire': grimoire,
        'snapshot': snapshot,
        'timeshift': timeshift,
        'vanish': vanish,
        'shroud': shroud,
    }
    
    cmd = ''
    logging.info('Keeper plugin started')
    
    while cmd != SHUTDOWN_COMMAND:
        response = None
        input_data = read_command()
        if input_data is None:
            logging.error('Error reading command')
            continue
        
        logging.info(f'Received input: {input_data}')
        
        if TOOL_CALLS_PROPERTY in input_data:
            tool_calls = input_data[TOOL_CALLS_PROPERTY]
            for tool_call in tool_calls:
                if FUNCTION_PROPERTY in tool_call:
                    cmd = tool_call[FUNCTION_PROPERTY]
                    logging.info(f'Processing command: {cmd}')
                    if cmd in commands:
                        if cmd == INITIALIZE_COMMAND or cmd == SHUTDOWN_COMMAND:
                            response = commands[cmd]()
                        else:
                            execute_initialize_command()
                            params = tool_call.get(PARAMS_PROPERTY, {})
                            context = tool_call.get(CONTEXT_PROPERTY, {})
                            system_info = tool_call.get(SYSTEM_INFO_PROPERTY, {})
                            logging.info(f'Executing command: {cmd} with params: {params}')
                            response = commands[cmd](params, context, system_info)
                    else:
                        logging.warning(f'Unknown command: {cmd}')
                        response = generate_failure_response(f'Unknown command: {cmd}')
                else:
                    logging.warning('Malformed input: missing function property')
                    response = generate_failure_response('Malformed input.')
        else:
            logging.warning('Malformed input: missing tool_calls property')
            response = generate_failure_response('Malformed input.')
        
        logging.info(f'Sending response: {response}')
        write_response(response)
        
        if cmd == SHUTDOWN_COMMAND:
            logging.info('Shutdown command received, terminating plugin')
            break
    
    logging.info('Keeper plugin stopped.')
    return 0


if __name__ == "__main__":
    main()