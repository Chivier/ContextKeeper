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
DATA_DIR = Path.home() / ".context_keeper" / "contexts"

LOG_FILE = Path.home() / "context_keeper_plugin.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

INDEX_FILE = Path.home() / ".context_keeper" / "index.json"


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
        
    def save_context(self, context_name: str) -> Dict:
        """Save complete context as per DESIGN.md"""
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
            
            # Save environment variables with timestamp
            env_path = self.env_manager.save_environment(context_name)
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
            
            self.logger.info(f"Context '{context_name}' saved successfully")
            return context_data
            
        except Exception as e:
            self.logger.error(f"Error saving context: {e}\n{traceback.format_exc()}")
            raise
    
    def _save_system_state(self) -> Dict:
        """Save system-level state"""
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
        """Save clipboard content"""
        try:
            clipboard_data = pyperclip.paste()
            clipboard_path = DATA_DIR / context_name / "clipboard_cache.txt"
            clipboard_path.parent.mkdir(parents=True, exist_ok=True)
            clipboard_path.write_text(clipboard_data, encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Failed to save clipboard: {e}")
    
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


def quick_save(*_):
    context_name = "auto-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        context_keeper.save_context(context_name)
        log_context(context_name)
        return generate_success_response(f"Quick saved as '{context_name}'")
    except Exception as e:
        return generate_failure_response(f"Quick save failed: {str(e)}")


def quick_switch(*_):
    if not INDEX_FILE.exists():
        return generate_failure_response("No recent contexts available.")
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except:
        return generate_failure_response("Index file corrupted.")

    if not index:
        return generate_failure_response("Context list is empty.")
    # Restore most recent context
    context_name = index[0]
    return restore_context({"context_name": context_name})


def clear_windows(*_):
    temp_name = "autosave-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Check for unsaved documents before closing
        unsaved_docs = context_keeper.document_tracker.check_unsaved_documents()
        if unsaved_docs:
            doc_list = "\n".join([f"- {doc['application']}: {doc['title']}" for doc in unsaved_docs])
            logging.warning(f"Found {len(unsaved_docs)} unsaved documents:\n{doc_list}")
            # In a real implementation, this would prompt the user
        
        # Save context first
        context_keeper.save_context(temp_name)
        log_context(temp_name)
        
        # Close all windows (excluding system processes)
        counts = context_keeper.windows_manager.close_all_windows(force=False)
        
        return generate_success_response(
            f"Context saved as '{temp_name}'. "
            f"Closed: {counts['closed']} windows, "
            f"Failed: {counts['failed']}, "
            f"Excluded: {counts['excluded']} system processes."
        )
    except Exception as e:
        return generate_failure_response(f"Clear windows failed: {str(e)}")


def minimize_windows(*_):
    """Safer alternative that just minimizes windows instead of closing them"""
    temp_name = "autosave-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        context_keeper.save_context(temp_name)
        log_context(temp_name)
        
        # Minimize all windows
        count = context_keeper.windows_manager.minimize_all_windows()
        
        return generate_success_response(f"Context saved as '{temp_name}' and {count} windows minimized.")
    except Exception as e:
        return generate_failure_response(f"Minimize windows failed: {str(e)}")


def save_context(params=None, *_):
    context_name = params.get("context_name", "unnamed")
    try:
        context_keeper.save_context(context_name)
        log_context(context_name)
        return generate_success_response(f"Context '{context_name}' saved.")
    except Exception as e:
        return generate_failure_response(f"Save failed: {str(e)}")


def restore_context(params=None, *_):
    context_name = params.get("context_name", "")
    if not context_name:
        return generate_failure_response("Context name required.")
        
    try:
        if context_keeper.restore_context(context_name):
            return generate_success_response(f"Context '{context_name}' restored.")
        else:
            return generate_failure_response(f"Context '{context_name}' not found.")
    except Exception as e:
        return generate_failure_response(f"Restore failed: {str(e)}")


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
    commands = {
        "initialize": execute_initialize_command,
        "shutdown": execute_shutdown_command,
        "save_context": save_context,
        "restore_context": restore_context,
        "quick_save": quick_save,
        "quick_switch": quick_switch,
        "clear_windows": clear_windows,
        "minimize_windows": minimize_windows,
    }
    cmd = ""
    while cmd != "shutdown":
        input_data = read_command()
        if input_data and "tool_calls" in input_data:
            for call in input_data["tool_calls"]:
                func = call.get("func", "")
                props = call.get("properties", {})
                if func in commands:
                    cmd = func
                    response = commands[func](props)
                else:
                    response = generate_failure_response("Unknown function")
                write_response(response)
        else:
            write_response(generate_failure_response("Malformed input"))


if __name__ == "__main__":
    main()