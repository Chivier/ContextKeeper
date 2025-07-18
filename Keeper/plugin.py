import json
import logging
import os
from ctypes import byref, windll, wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import traceback

# Handle optional imports gracefully
try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not available - process names will be limited")

try:
    import pygetwindow as gw
except ImportError:
    gw = None
    logging.warning("pygetwindow not available")

try:
    import pyperclip
except ImportError:
    pyperclip = None
    logging.warning("pyperclip not available - clipboard operations disabled")

# Import our components
from environment_manager import EnvironmentManager
from windows_context_manager import WindowsContextManager, WindowInfo
from browser_tab_extractor import BrowserTabExtractor
try:
    from browser_tab_extractor_fast import FastBrowserTabExtractor
except ImportError:
    FastBrowserTabExtractor = None
from terminal_manager import TerminalManager
from ide_tracker import IDETracker
from document_tracker import DocumentTracker
from whitelist_manager import WhitelistManager

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
    """Main context keeper implementation using all components.
    
    This class coordinates all subsystems to provide complete workspace management:
    - Window enumeration and positioning
    - Browser tab extraction
    - Environment variable capture
    - Terminal state preservation
    - IDE and document tracking
    - Whitelist management for protection
    """
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.windows_manager = WindowsContextManager()
        self.browser_extractor = BrowserTabExtractor()
        self.fast_browser_extractor = FastBrowserTabExtractor() if FastBrowserTabExtractor else None
        self.terminal_manager = TerminalManager()
        self.ide_tracker = IDETracker()
        self.document_tracker = DocumentTracker()
        self.whitelist_manager = WhitelistManager()
        self.logger = logging.getLogger(__name__)
        self._last_context_time = 0
        self._context_cache = None
        
    def keep_context(self, context_name: str, quick_mode: bool = False) -> Dict:
        """Save the complete workspace context.
        
        Args:
            context_name: Name to save the context as
            quick_mode: If True, skips time-consuming operations like:
                       - Document state checking
                       - Favicon fetching
                       - Environment cleanup
                       
        Returns:
            Dict containing all captured context data including:
            - Windows and their positions
            - Browser tabs
            - Environment variables
            - Application states
        """
        import time
        start_time = time.time()
        
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
            self.logger.info(f"Starting context save for '{context_name}'")
            # Skip document check in quick mode
            if not quick_mode:
                unsaved_docs = self.document_tracker.check_unsaved_documents()
                if unsaved_docs:
                    self.logger.warning(f"Found {len(unsaved_docs)} unsaved documents")
                
            # Save system state
            context_data["windows"]["system"] = self._save_system_state()
            
            # Keep environment variables with timestamp
            env_path = self.env_manager.keep_environment(context_name)
            context_data["environmentSnapshot"] = env_path
            
            # Get current environment for immediate reference
            context_data["environmentVariables"] = dict(os.environ)
            
            # Save clipboard
            self._save_clipboard(context_name)
            
            # Skip document states in quick mode
            if not quick_mode:
                document_states = self.document_tracker.get_document_states()
                context_data["documents"] = document_states
            
            # Get all windows
            windows = self.windows_manager.enum_windows()
            self.logger.info(f"Found {len(windows)} windows to process")
            
            # Debug: Log window details
            for window in windows:
                self.logger.info(f"Window: {window.title[:50]}... Process: {window.process_name}")
            
            # Process windows by type
            for window in windows:
                self._process_window(window, context_data, quick_mode)
            
            # Save the main context file
            context_path = DATA_DIR / context_name
            context_path.mkdir(parents=True, exist_ok=True)
            
            with open(context_path / "context.json", "w", encoding="utf-8") as f:
                json.dump(context_data, f, indent=2)
                
            # Skip cleanup in quick mode
            if not quick_mode:
                self.env_manager.cleanup_old_snapshots(context_name, keep_last=10)
            
            elapsed = time.time() - start_time
            self.logger.info(f"Context '{context_name}' kept successfully in {elapsed:.2f} seconds")
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
        if not pyperclip:
            self.logger.debug("Clipboard capture skipped - pyperclip not available")
            return
            
        try:
            clipboard_data = pyperclip.paste()
            clipboard_path = DATA_DIR / context_name / "clipboard_cache.txt"
            clipboard_path.parent.mkdir(parents=True, exist_ok=True)
            clipboard_path.write_text(clipboard_data, encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Failed to capture clipboard: {e}")
    
    def _process_window(self, window: WindowInfo, context_data: Dict, quick_mode: bool = False):
        """Process a window and categorize it by type.
        
        This method examines each window and routes it to the appropriate
        handler based on the process name:
        - Browsers (Chrome, Edge, Firefox)
        - Terminals (Windows Terminal, PowerShell, CMD)
        - IDEs (VSCode, Cursor, JetBrains)
        - Other applications
        
        Args:
            window: WindowInfo object containing window details
            context_data: Dictionary to store the categorized window data
            quick_mode: Whether to use fast extraction methods
        """
        process_name = window.process_name.lower()
        self.logger.debug(f"Processing window: {window.title[:30]}... from process: {process_name}")
        
        # Check if it's a browser
        if any(browser in process_name for browser in ['chrome', 'firefox', 'edge', 'msedge']):
            self.logger.info(f"Found browser window: {process_name}")
            self._process_browser_window(window, context_data, quick_mode)
        # Check if it's a terminal
        elif any(term in process_name for term in ['terminal', 'cmd', 'powershell', 'pwsh', 'termius']):
            self.logger.info(f"Found terminal window: {process_name}")
            self._process_terminal_window(window, context_data)
        # Check if it's an IDE
        elif any(ide in process_name for ide in ['code', 'cursor', 'pycharm', 'idea', 'sublime', 'notepad++']):
            self.logger.info(f"Found IDE window: {process_name}")
            self._process_ide_window(window, context_data)
        # Other applications
        else:
            self.logger.debug(f"Found other application: {process_name}")
            self._process_application_window(window, context_data)
    
    def _process_browser_window(self, window: WindowInfo, context_data: Dict, quick_mode: bool = False):
        """Process browser window"""
        browser_type = 'chrome'
        if 'firefox' in window.process_name.lower():
            browser_type = 'firefox'
        elif 'edge' in window.process_name.lower():
            browser_type = 'edge'
            
        # Get tabs
        tabs_result = []
        active_index = 0
        
        # Use fast extractor in quick mode
        extractor = self.fast_browser_extractor if (quick_mode and self.fast_browser_extractor) else self.browser_extractor
        
        if browser_type == 'chrome':
            result = extractor.extract_chrome_tabs()
        elif browser_type == 'edge':
            result = extractor.extract_edge_tabs()
        elif browser_type == 'firefox':
            result = extractor.extract_firefox_tabs() if not quick_mode else []
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
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd),
                "zOrder": window.z_order
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
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd),
                "zOrder": window.z_order
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
                    "virtualDesktop": 1,  # Would need virtual desktop detection
                    "zOrder": window.z_order
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
                "virtualDesktop": self._get_window_virtual_desktop(window.hwnd),
                "zOrder": window.z_order
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
                if pyperclip:
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
        
        # Create a list of all saved windows with their data
        all_saved_windows = []
        
        # Add applications
        for app in context_data.get("windows", {}).get("applications", []):
            window_data = app.get("window", {})
            window_data["processName"] = app.get("processName", "")
            window_data["title"] = app.get("title", "")
            all_saved_windows.append(window_data)
            
        # Add browsers
        for browser in context_data.get("browsers", []):
            window_data = browser.get("window", {})
            window_data["processName"] = browser.get("processName", "")
            all_saved_windows.append(window_data)
        
        # Sort saved windows by Z-order (lowest z_order = topmost)
        all_saved_windows.sort(key=lambda w: w.get("zOrder", 999))
        
        # Create process name mapping for quick lookup
        saved_by_process = {}
        for saved in all_saved_windows:
            process_name = saved.get("processName", "").lower()
            if process_name not in saved_by_process:
                saved_by_process[process_name] = []
            saved_by_process[process_name].append(saved)
        
        # Restore windows in reverse Z-order (bottom to top)
        for saved_window in reversed(all_saved_windows):
            process_name = saved_window.get("processName", "").lower()
            
            # Find matching current window
            for window in current_windows:
                if window.process_name.lower() == process_name:
                    self.windows_manager.restore_window_position(
                        window.hwnd,
                        saved_window.get("x", window.x),
                        saved_window.get("y", window.y),
                        saved_window.get("width", window.width),
                        saved_window.get("height", window.height),
                        saved_window.get("state") == "maximized",
                        saved_window.get("state") == "minimized"
                    )
                    
                    # Bring window to correct Z-order position
                    if saved_window.get("zOrder", 999) < 100:  # Only for reasonably positioned windows
                        try:
                            # Use SetWindowPos to set Z-order
                            HWND_TOP = 0
                            SWP_NOMOVE = 0x0002
                            SWP_NOSIZE = 0x0001
                            self.windows_manager.user32.SetWindowPos(
                                window.hwnd, HWND_TOP,
                                0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE
                            )
                        except:
                            pass
                    break
    
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
        # Log the intent immediately
        log_context(context_name)
        
        # Start saving in background
        import threading
        save_result = {}
        
        def save_context():
            try:
                save_result['data'] = context_keeper.keep_context(context_name, quick_mode=True)
            except Exception as e:
                save_result['error'] = str(e)
        
        thread = threading.Thread(target=save_context)
        thread.start()
        
        # Wait briefly (max 0.3 seconds)
        thread.join(timeout=0.3)
        
        if thread.is_alive():
            # Still saving, return quick response
            message = f"⚡ **Quick Save in Progress!**\n\n"
            message += f"📌 **Saving as:** `{context_name}`\n\n"
            message += "💡 **Tip:** Say 'Quick switch' to restore once complete!"
            return generate_success_response(message)
        
        # Save completed, show full stats
        if 'error' in save_result:
            raise Exception(save_result['error'])
            
        context_data = save_result.get('data', {})
        
        # Count items for summary
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        total_tabs = sum(len(b.get("tabs", [])) for b in context_data.get("browsers", []))
        
        message = f"⚡ **Quick Save Complete!**\n\n"
        message += f"📌 **Auto-saved as:** `{context_name}`\n\n"
        message += f"📊 **Captured:**\n"
        message += f"  🪟 {windows_count} windows\n"
        message += f"  🌐 {total_tabs} browser tabs\n\n"
        message += "💡 **Tip:** Say 'Quick switch' to instantly restore this workspace!"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Quick keep failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Quick save failed: {str(e)}")


def quick_switch(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    if not INDEX_FILE.exists():
        return generate_failure_response("📭 No recent workspaces available. Save one with 'Quick save' first!")
    
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except:
        return generate_failure_response("⚠️ Index file corrupted.")

    if not index:
        return generate_failure_response("📭 No recent workspaces found.")
    
    # Show recent contexts list
    message = "🕒 **Recent Workspaces**\n\n"
    for i, ctx in enumerate(index[:5], 1):
        if i == 1:
            message += f"**{i}. {ctx}** ← _switching to this_\n"
        else:
            message += f"{i}. {ctx}\n"
    
    if len(index) > 5:
        message += f"_...and {len(index) - 5} more_\n"
    
    message += "\n⏳ Restoring workspace...\n"
    
    # Restore most recent context
    context_name = index[0]
    return restore_context({"context_name": context_name}, context, system_info)


def list_contexts(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """List all saved contexts with details"""
    try:
        contexts = context_keeper.list_contexts()
        
        if not contexts:
            return generate_success_response("📭 No saved workspaces found. Start saving with 'Save workspace as [name]'!")
        
        message = f"📚 **Your Saved Workspaces ({len(contexts)} total)**\n\n"
        
        for i, ctx_name in enumerate(contexts[:10], 1):  # Show max 10
            try:
                context_path = DATA_DIR / ctx_name / "context.json"
                with open(context_path, "r", encoding="utf-8") as f:
                    ctx_data = json.load(f)
                
                # Get stats
                windows_count = len(ctx_data.get("windows", {}).get("applications", []))
                browsers_count = len(ctx_data.get("browsers", []))
                total_tabs = sum(len(b.get("tabs", [])) for b in ctx_data.get("browsers", []))
                timestamp = ctx_data.get("timestamp", "Unknown")
                
                # Format timestamp nicely
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%b %d at %I:%M %p")
                except:
                    time_str = timestamp
                
                message += f"**{i}. {ctx_name}**\n"
                message += f"   📅 Saved: {time_str}\n"
                message += f"   📊 {windows_count} windows, {total_tabs} tabs\n\n"
                
            except Exception as e:
                message += f"**{i}. {ctx_name}** ⚠️ (Error reading)\n\n"
        
        if len(contexts) > 10:
            message += f"\n_...and {len(contexts) - 10} more workspaces_\n\n"
        
        message += "💡 **Tip:** Say 'Restore [workspace-name]' to switch to any saved workspace!"
        
        return generate_success_response(message.rstrip())
        
    except Exception as e:
        logging.error(f"List contexts failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Failed to list workspaces: {str(e)}")


def clear_windows(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Save context and close all windows (with optional aggressive mode).
    
    This function provides a clean desktop by closing all applications
    while preserving the current state for later restoration.
    
    Modes:
    - Normal: Checks for unsaved documents, closes gracefully
    - Aggressive: Force terminates processes, skips safety checks
    
    Both modes respect the whitelist (NVIDIA apps, G-Assist, etc.)
    
    Args:
        params: Dict with optional 'aggressive' boolean flag
        
    Returns:
        Success response with closure statistics
    """
    temp_name = "autokeep-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    aggressive = params.get("aggressive", False) if params else False
    
    try:
        # Log the intent immediately
        log_context(temp_name)
        
        # Check for unsaved documents before closing
        unsaved_count = 0
        if not aggressive:  # Skip check in aggressive mode
            unsaved_docs = context_keeper.document_tracker.check_unsaved_documents()
            unsaved_count = len(unsaved_docs)
            if unsaved_docs:
                doc_list = "\n".join([f"- {doc['application']}: {doc['title']}" for doc in unsaved_docs])
                logging.warning(f"Found {unsaved_count} unsaved documents:\n{doc_list}")
        
        # Start context saving in background
        import threading
        save_result = {}
        
        def save_context():
            try:
                save_result['context'] = context_keeper.keep_context(temp_name, quick_mode=True)
            except Exception as e:
                save_result['error'] = str(e)
        
        save_thread = threading.Thread(target=save_context)
        save_thread.start()
        
        # Close windows immediately (this is usually fast)
        counts = context_keeper.windows_manager.close_all_windows(
            force=aggressive,
            whitelist_checker=context_keeper.whitelist_manager.is_whitelisted
        )
        
        # Wait briefly for save to complete (max 0.2 seconds)
        save_thread.join(timeout=0.2)
        
        # Build response message
        message = f"🧽 **Desktop Cleared!**\n\n"
        
        if save_thread.is_alive():
            # Still saving, show minimal info
            message += f"💾 **Saving workspace...** (as `{temp_name}`)\n\n"
        else:
            # Save completed
            message += f"💾 **Auto-saved as:** `{temp_name}`\n\n"
        
        if aggressive:
            message += "⚠️ **Mode:** Aggressive (force-closed)\n\n"
        elif unsaved_count > 0:
            message += f"⚠️ **Warning:** {unsaved_count} unsaved documents\n\n"
        
        message += f"📊 **Results:**\n"
        message += f"  ✅ Closed: {counts['closed']} windows\n"
        if counts['failed'] > 0:
            message += f"  ❌ Failed: {counts['failed']}\n"
        if counts.get('whitelisted', 0) > 0:
            message += f"  🔒 Protected: {counts.get('whitelisted', 0)} (whitelisted)\n"
        message += f"  🔧 System: {counts['excluded']} processes kept\n\n"
        
        message += "💡 **Tip:** Use 'Quick switch' to restore your desktop instantly!"
        
        return generate_success_response(message)
    except Exception as e:
        return generate_failure_response(f"❌ Clear windows failed: {str(e)}")


def minimize_windows(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Save context and minimize all windows (safer than closing).
    
    This function provides a clean desktop without closing applications.
    It respects the whitelist, keeping specified apps visible.
    
    Whitelisted apps (always visible):
    - NVIDIA App
    - Project G-Assist
    - System processes
    - User-defined apps
    
    Returns:
        Success response with minimize statistics
    """
    temp_name = "autokeep-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        # Log the intent immediately
        log_context(temp_name)
        
        # Start context saving in background
        import threading
        save_result = {}
        
        def save_context():
            try:
                save_result['context'] = context_keeper.keep_context(temp_name, quick_mode=True)
            except Exception as e:
                save_result['error'] = str(e)
        
        save_thread = threading.Thread(target=save_context)
        save_thread.start()
        
        # Minimize windows immediately
        counts = context_keeper.windows_manager.minimize_all_windows(
            whitelist_checker=context_keeper.whitelist_manager.is_whitelisted
        )
        
        # Wait briefly for save to complete (max 0.2 seconds)
        save_thread.join(timeout=0.2)
        
        # Build response message
        message = f"🖼️ **Desktop Minimized!**\n\n"
        
        if save_thread.is_alive():
            # Still saving, show minimal info
            message += f"💾 **Saving workspace...** (as `{temp_name}`)\n\n"
        else:
            # Save completed
            message += f"💾 **Auto-saved as:** `{temp_name}`\n\n"
        
        message += f"📊 **Results:**\n"
        message += f"  📥 Minimized: {counts['minimized']} windows\n"
        if counts['skipped'] > 0:
            message += f"  👀 Kept visible: {counts['skipped']} (whitelisted)\n\n"
        else:
            message += "\n"
        
        message += "💡 **Tip:** Your apps are still running! Say 'Quick switch' to restore the layout."
        
        return generate_success_response(message)
    except Exception as e:
        return generate_failure_response(f"❌ Minimize windows failed: {str(e)}")


def memorize(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Save the current workspace context.
    
    This is the main entry point for saving workspaces. It supports multiple
    parameter names for flexibility:
    - 'realm' or 'project': Primary parameter names
    - 'realm_name' or 'context_name': Legacy compatibility
    
    The function uses threading for quick response times:
    1. In quick mode (default), it responds within 0.3s
    2. If save completes quickly, returns full statistics
    3. If still saving, returns "saving..." message
    
    Args:
        params: Dict containing context name and options
        context: G-Assist conversation context (unused)
        system_info: System information from G-Assist (unused)
        
    Returns:
        Success response with save statistics or progress message
    """
    if not params:
        return generate_failure_response("Parameters required.")
    
    # Support multiple parameter names: realm as project, realm_name, and context_name
    context_name = params.get("realm") or params.get("project") or params.get("realm_name") or params.get("context_name", "unnamed")
    quick_mode = params.get("quick", True)  # Default to quick mode for better performance
    
    try:
        # For quick response, save minimal context first
        if quick_mode:
            # Just log the intent immediately
            log_context(context_name)
            
            # Start the actual save in a thread
            import threading
            save_result = {}
            
            def save_context():
                save_result['data'] = context_keeper.keep_context(context_name, quick_mode=True)
            
            thread = threading.Thread(target=save_context)
            thread.start()
            
            # Wait briefly (max 0.3 seconds for faster response)
            thread.join(timeout=0.3)
            
            if thread.is_alive():
                # Return immediate response while save continues
                return generate_success_response(f"💾 Saving **{context_name}** workspace...")
            else:
                # Completed quickly, return full details
                context_data = save_result.get('data', {})
        else:
            # Full mode - do everything synchronously
            context_data = context_keeper.keep_context(context_name, quick_mode=quick_mode)
            log_context(context_name)
        
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
        
        # Build beautiful response message with emojis and formatting
        message = f"✅ **{context_name}** workspace saved successfully!\n\n"
        message += f"📊 **Captured Items:**\n"
        message += f"  🪟 Windows: **{windows_count}** applications\n"
        message += f"  🌐 Browser tabs: **{total_tabs}** tabs"
        if browsers_count > 1:
            message += f" ({browsers_count} browsers)"
        message += "\n"
        
        if total_files > 0:
            message += f"  💻 IDE files: **{total_files}** open files\n"
        if terminal_tabs > 0:
            message += f"  🖥️ Terminal sessions: **{terminal_tabs}** active terminals\n"
        if env_vars_count > 0:
            message += f"  🔧 Environment: **{env_vars_count}** variables captured\n"
        
        message += f"\n💡 **Tip:** Use 'Restore {context_name}' to bring back this exact setup!"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Keep context failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Failed to save workspace '{context_name}': {str(e)}")


def add_to_whitelist(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Add an application to the minimize whitelist"""
    if not params:
        return generate_failure_response("Parameters required.")
    
    app_name = params.get("app_name", "").strip()
    if not app_name:
        return generate_failure_response("Application name required.")
    
    try:
        added = context_keeper.whitelist_manager.add_to_whitelist(app_name)
        if added:
            message = f"✅ **Added to Whitelist**\n\n"
            message += f"📌 **Application:** {app_name}\n\n"
            message += "ℹ️ This app will stay visible when you minimize or clear windows."
            return generate_success_response(message)
        else:
            return generate_success_response(f"ℹ️ '{app_name}' is already in the whitelist.")
    except Exception as e:
        logging.error(f"Add to whitelist failed: {e}")
        return generate_failure_response(f"❌ Failed to add to whitelist: {str(e)}")


def remove_from_whitelist(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Remove an application from the minimize whitelist"""
    if not params:
        return generate_failure_response("Parameters required.")
    
    app_name = params.get("app_name", "").strip()
    if not app_name:
        return generate_failure_response("Application name required.")
    
    try:
        removed = context_keeper.whitelist_manager.remove_from_whitelist(app_name)
        if removed:
            message = f"🗑️ **Removed from Whitelist**\n\n"
            message += f"📌 **Application:** {app_name}\n\n"
            message += "ℹ️ This app will now be minimized with other windows."
            return generate_success_response(message)
        else:
            return generate_success_response(f"⚠️ '{app_name}' was not in whitelist or is a protected system app.")
    except Exception as e:
        logging.error(f"Remove from whitelist failed: {e}")
        return generate_failure_response(f"❌ Failed to remove from whitelist: {str(e)}")


def list_whitelist(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """List all applications in the minimize whitelist"""
    try:
        whitelist = context_keeper.whitelist_manager.list_whitelist()
        
        if not whitelist:
            return generate_success_response("📭 The whitelist is empty. Add apps with 'Add [app-name] to whitelist'.")
        
        message = f"🔒 **Protected Applications ({len(whitelist)} total)**\n\n"
        message += "These apps stay visible when minimizing windows:\n\n"
        
        # Separate system apps from user apps
        system_apps = []
        user_apps = []
        
        for app in whitelist:
            if app.lower() in ['explorer.exe', 'dwm.exe', 'shellexperiencehost.exe', 'searchhost.exe', 'textinputhost.exe']:
                system_apps.append(app)
            else:
                user_apps.append(app)
        
        if user_apps:
            message += "📌 **User Apps:**\n"
            for app in user_apps:
                message += f"  • {app}\n"
            message += "\n"
        
        if system_apps:
            message += "🔧 **System Apps:**\n"
            for app in system_apps:
                message += f"  • {app}\n"
            message += "\n"
        
        message += "💡 **Tip:** Remove apps with 'Remove [app-name] from whitelist'."
        
        return generate_success_response(message.rstrip())
    except Exception as e:
        logging.error(f"List whitelist failed: {e}")
        return generate_failure_response(f"❌ Failed to list whitelist: {str(e)}")


def clear_history(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Clear/delete a specific saved context - only deletes saved data, does not close windows"""
    if not params:
        return generate_failure_response("Parameters required.")
    
    # Support multiple parameter names like memorize function
    context_name = params.get("realm") or params.get("project") or params.get("realm_name") or params.get("context_name", "")
    context_name = context_name.strip()
    if not context_name:
        return generate_failure_response("Context name required.")
    
    try:
        context_path = DATA_DIR / context_name
        
        # Check if context exists
        if not context_path.exists():
            return generate_failure_response(f"❌ Workspace '{context_name}' not found.")
        
        # Get info about the context before deleting
        try:
            with open(context_path / "context.json", "r", encoding="utf-8") as f:
                ctx_data = json.load(f)
            timestamp = ctx_data.get('timestamp', 'Unknown')
        except:
            timestamp = 'Unknown'
        
        # Remove the context directory and all its contents
        import shutil
        shutil.rmtree(context_path)
        
        # Remove from index if exists
        if INDEX_FILE.exists():
            try:
                index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
                if context_name in index:
                    index.remove(context_name)
                    INDEX_FILE.write_text(json.dumps(index, indent=2))
            except:
                pass
        
        logging.info(f"Cleared context history for '{context_name}'")
        
        message = f"🗑️ **Workspace Deleted**\n\n"
        message += f"📌 **Name:** {context_name}\n"
        message += f"📅 **Was saved:** {timestamp}\n\n"
        message += "ℹ️ This only deleted the saved workspace data. Your current windows remain open."
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Clear history failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Failed to delete workspace '{context_name}': {str(e)}")


def clear_all_history(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    """Clear all saved contexts - only deletes saved data, does not close windows"""
    try:
        # Count contexts before deletion
        contexts = context_keeper.list_contexts()
        count = len(contexts)
        
        if count == 0:
            return generate_success_response("📭 No saved workspaces to delete.")
        
        # Remove all context directories
        import shutil
        deleted_count = 0
        if DATA_DIR.exists():
            for context_dir in DATA_DIR.iterdir():
                if context_dir.is_dir():
                    try:
                        shutil.rmtree(context_dir)
                        deleted_count += 1
                    except Exception as e:
                        logging.error(f"Failed to remove {context_dir}: {e}")
        
        # Clear the index file
        if INDEX_FILE.exists():
            INDEX_FILE.write_text(json.dumps([], indent=2))
        
        logging.info(f"Cleared all {deleted_count} contexts")
        
        message = f"🧽 **All Workspaces Cleared**\n\n"
        message += f"🗑️ **Deleted:** {deleted_count} saved workspaces\n\n"
        message += "ℹ️ This only deleted the saved workspace data. Your current windows remain open.\n\n"
        message += "💡 **Tip:** Start fresh by saving a new workspace with 'Save workspace as [name]'!"
        
        return generate_success_response(message)
        
    except Exception as e:
        logging.error(f"Clear all history failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Failed to clear all workspaces: {str(e)}")


def restore_context(params: dict = None, context: dict = None, system_info: dict = None) -> dict:
    if not params:
        return generate_failure_response("Parameters required.")
    context_name = params.get("context_name", "")
    if not context_name:
        return generate_failure_response("Context name required.")
        
    try:
        # Check if context exists
        context_path = DATA_DIR / context_name / "context.json"
        if not context_path.exists():
            return generate_failure_response(f"❌ Workspace '{context_name}' not found.")
        
        # Load context data to show what will be restored
        with open(context_path, "r", encoding="utf-8") as f:
            context_data = json.load(f)
        
        # Count items
        windows_count = len(context_data.get("windows", {}).get("applications", []))
        browsers_count = len(context_data.get("browsers", []))
        total_tabs = sum(len(b.get("tabs", [])) for b in context_data.get("browsers", []))
        timestamp = context_data.get('timestamp', 'Unknown')
        
        # Perform the restoration
        success = context_keeper.restore_context(context_name)
        
        if success:
            message = f"🔄 **{context_name}** workspace restored!\n\n"
            message += f"✨ **Restored Items:**\n"
            message += f"  🪟 {windows_count} windows positioned\n"
            message += f"  🌐 {total_tabs} browser tabs opened\n"
            message += f"  🔧 Environment variables applied\n\n"
            message += f"⏰ **Originally saved:** {timestamp}\n\n"
            message += "💡 Your workspace is back exactly as you left it!"
            return generate_success_response(message)
        else:
            return generate_failure_response(f"❌ Failed to restore workspace '{context_name}'.")
            
    except Exception as e:
        logging.error(f"Restore context failed: {e}\n{traceback.format_exc()}")
        return generate_failure_response(f"❌ Failed to restore workspace '{context_name}': {str(e)}")


def read_command() -> dict | None:
    """Read a command from G-Assist via stdin pipe.
    
    G-Assist sends commands as JSON through a named pipe.
    This function reads chunks until the complete message is received.
    
    Returns:
        Parsed JSON command or None if read fails
    """
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
    """Write a response back to G-Assist via stdout pipe.
    
    IMPORTANT: The response must end with <<END>> marker
    or G-Assist will timeout waiting for more data.
    
    Args:
        response: Dict with 'success' and 'message' keys
    """
    try:
        STD_OUTPUT_HANDLE = -11
        pipe = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        # Critical: Add <<END>> terminator
        json_message = json.dumps(response) + "<<END>>"
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
    """Main plugin loop implementing G-Assist communication protocol.
    
    This function:
    1. Reads commands from stdin (named pipe from G-Assist)
    2. Parses JSON command structure
    3. Routes to appropriate handler function
    4. Sends JSON response with <<END>> terminator
    5. Continues until shutdown command received
    
    Protocol format:
    Input: {"tool_calls": [{"func": "command_name", "params": {...}}]}
    Output: {"success": true/false, "message": "..."}
    """
    # G-Assist protocol constants
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
        'keep_context': memorize,  # Using memorize function which has proper parameter handling
        'restore_context': restore_context,
        'list_contexts': list_contexts,
        'quick_keep': quick_keep,
        'quick_switch': quick_switch,
        'clear_windows': clear_windows,
        'minimize_windows': minimize_windows,
        'memorize': memorize,  # Add direct memorize command
        'add_to_whitelist': add_to_whitelist,
        'remove_from_whitelist': remove_from_whitelist,
        'list_whitelist': list_whitelist,
        'clear_history': clear_history,
        'clear_all_history': clear_all_history,
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