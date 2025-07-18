import ctypes
import ctypes.wintypes
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

# Handle optional psutil import
try:
    import psutil
except ImportError:
    psutil = None


# Define WINDOWPLACEMENT structure since it's not in ctypes.wintypes
class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", ctypes.wintypes.POINT),
        ("ptMaxPosition", ctypes.wintypes.POINT),
        ("rcNormalPosition", ctypes.wintypes.RECT)
    ]


@dataclass
class WindowInfo:
    """Information about a window"""
    hwnd: int
    title: str
    process_name: str
    process_id: int
    x: int
    y: int
    width: int
    height: int
    is_maximized: bool
    is_minimized: bool
    is_visible: bool
    z_order: int = 0  # Window stacking order (0 = topmost)


class WindowsContextManager:
    """Manages Windows-specific context operations using Windows API.
    
    This class provides low-level Windows integration for:
    - Window enumeration with Z-order tracking
    - Process name resolution (with psutil fallback)
    - Window state capture (position, size, maximized/minimized)
    - Window restoration with proper layering
    - Minimize/close operations with safety checks
    
    Uses ctypes for direct Windows API access for maximum compatibility.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Declare Windows API functions that might not be available
        try:
            self.kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.DWORD,
                ctypes.wintypes.LPWSTR,
                ctypes.POINTER(ctypes.wintypes.DWORD)
            ]
            self.kernel32.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL
        except:
            pass
        
    def enum_windows(self) -> List[WindowInfo]:
        """Enumerate all visible windows with complete information.
        
        This method performs two passes:
        1. First pass: Build Z-order map using GetTopWindow/GetWindow chain
           This gives us the exact stacking order of windows
        2. Second pass: Use EnumWindows to get all window details
           EnumWindows is more reliable but doesn't provide Z-order
           
        The combination ensures we get all windows with correct layering.
        
        Returns:
            List of WindowInfo objects sorted by Z-order (topmost first)
        """
        windows = []
        
        # First get Z-order using GetTopWindow/GetWindow
        z_order_map = {}
        z_index = 0
        hwnd = self.user32.GetTopWindow(0)
        
        while hwnd:
            if self.user32.IsWindowVisible(hwnd):
                z_order_map[hwnd] = z_index
                z_index += 1
            hwnd = self.user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
        
        # Define callback function type
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM
        )
        
        def enum_windows_callback(hwnd, lParam):
            """Callback function for EnumWindows"""
            try:
                # Skip invisible windows
                if not self.user32.IsWindowVisible(hwnd):
                    return True
                
                # Get window title
                title = self._get_window_title(hwnd)
                if not title:
                    return True
                
                # Get window info with Z-order
                window_info = self._get_window_info(hwnd, z_order_map.get(hwnd, 999))
                if window_info:
                    windows.append(window_info)
                    
            except Exception as e:
                self.logger.warning(f"Error processing window {hwnd}: {e}")
                
            return True
        
        # Create callback and enumerate windows
        callback = EnumWindowsProc(enum_windows_callback)
        self.user32.EnumWindows(callback, 0)
        
        # Sort by Z-order
        windows.sort(key=lambda w: w.z_order)
        
        return windows
    
    def _get_window_title(self, hwnd: int) -> str:
        """Get window title"""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    
    def _get_window_info(self, hwnd: int, z_order: int = 999) -> Optional[WindowInfo]:
        """Get detailed window information"""
        try:
            # Get window title
            title = self._get_window_title(hwnd)
            if not title:
                return None
            
            # Get window rect
            rect = ctypes.wintypes.RECT()
            if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
            
            # Get process information
            process_id = ctypes.wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            
            # Get process name
            try:
                if psutil:
                    process = psutil.Process(process_id.value)
                    process_name = process.name()
                else:
                    raise ImportError("psutil not available")
            except Exception as e:
                # Fallback method using Windows API
                try:
                    # Open process with limited rights
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    h_process = self.kernel32.OpenProcess(
                        PROCESS_QUERY_LIMITED_INFORMATION,
                        False,
                        process_id.value
                    )
                    if h_process:
                        # Get process name
                        exe_name = ctypes.create_unicode_buffer(260)
                        size = ctypes.wintypes.DWORD(260)
                        if self.kernel32.QueryFullProcessImageNameW(
                            h_process, 0, exe_name, ctypes.byref(size)
                        ):
                            import os
                            process_name = os.path.basename(exe_name.value)
                        else:
                            process_name = "Unknown"
                        self.kernel32.CloseHandle(h_process)
                    else:
                        process_name = "Unknown"
                except:
                    process_name = "Unknown"
            
            # Get window state
            placement = WINDOWPLACEMENT()
            placement.length = ctypes.sizeof(WINDOWPLACEMENT)
            self.user32.GetWindowPlacement(hwnd, ctypes.byref(placement))
            
            is_maximized = placement.showCmd == 3  # SW_MAXIMIZE
            is_minimized = placement.showCmd == 2  # SW_MINIMIZE
            is_visible = self.user32.IsWindowVisible(hwnd)
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                process_id=process_id.value,
                x=rect.left,
                y=rect.top,
                width=rect.right - rect.left,
                height=rect.bottom - rect.top,
                is_maximized=is_maximized,
                is_minimized=is_minimized,
                is_visible=is_visible,
                z_order=z_order
            )
            
        except Exception as e:
            self.logger.warning(f"Error getting window info for {hwnd}: {e}")
            return None
    
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        """Find a window by its title"""
        windows = self.enum_windows()
        for window in windows:
            if title.lower() in window.title.lower():
                return window
        return None
    
    def get_windows_by_process(self, process_name: str) -> List[WindowInfo]:
        """Get all windows belonging to a specific process"""
        windows = self.enum_windows()
        return [w for w in windows if process_name.lower() in w.process_name.lower()]
    
    def restore_window_position(self, hwnd: int, x: int, y: int, width: int, height: int, 
                              is_maximized: bool = False, is_minimized: bool = False) -> bool:
        """Restore a window to a specific position and state"""
        try:
            # First restore the window if it's minimized
            if is_minimized:
                self.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            elif is_maximized:
                self.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            else:
                self.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                # Set window position
                self.user32.SetWindowPos(
                    hwnd, 0, x, y, width, height,
                    0x0040  # SWP_SHOWWINDOW
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring window position: {e}")
            return False
    
    def minimize_all_windows(self, whitelist_checker=None) -> Dict[str, int]:
        """Minimize all visible windows except whitelisted ones.
        
        This is a non-destructive operation that preserves all application
        states while providing a clean desktop. Whitelisted apps remain
        visible for continued use (e.g., NVIDIA apps, G-Assist).
        
        Args:
            whitelist_checker: Optional function that takes (process_name, window_title)
                             and returns True if window should stay visible
            
        Returns:
            Dict with counts: {'minimized': n, 'skipped': n}
        """
        counts = {'minimized': 0, 'skipped': 0}
        windows = self.enum_windows()
        
        for window in windows:
            if window.is_visible and not window.is_minimized:
                # Check whitelist if checker provided
                if whitelist_checker and whitelist_checker(window.process_name, window.title):
                    self.logger.info(f"Skipping whitelisted window: {window.title} [{window.process_name}]")
                    counts['skipped'] += 1
                    continue
                    
                try:
                    self.user32.ShowWindow(window.hwnd, 6)  # SW_MINIMIZE
                    counts['minimized'] += 1
                except:
                    pass
                    
        return counts
    
    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window"""
        hwnd = self.user32.GetForegroundWindow()
        if hwnd:
            return self._get_window_info(hwnd)
        return None
    
    def get_desktop_windows_order(self) -> List[int]:
        """Get windows in Z-order (front to back)"""
        z_order = []
        hwnd = self.user32.GetTopWindow(0)
        
        while hwnd:
            if self.user32.IsWindowVisible(hwnd):
                z_order.append(hwnd)
            hwnd = self.user32.GetWindow(hwnd, 2)  # GW_HWNDNEXT
            
        return z_order
    
    def close_all_windows(self, exclude_process_names: List[str] = None, force: bool = False, whitelist_checker=None) -> Dict[str, int]:
        """Close all visible windows with safety checks.
        
        This method attempts to close windows gracefully using WM_CLOSE.
        In aggressive mode (force=True), it will terminate processes that
        don't respond. System-critical processes are always protected.
        
        Safety features:
        - Default exclusion list for system stability
        - Whitelist support for user-protected apps
        - Graceful close attempt before force terminate
        - Skip already minimized windows
        
        Args:
            exclude_process_names: Additional processes to exclude
            force: Enable aggressive mode with process termination
            whitelist_checker: Function to check if app is protected
            
        Returns:
            Dict with counts: {'closed': n, 'failed': n, 'excluded': n, 'whitelisted': n}
        """
        if exclude_process_names is None:
            # Default exclusions to prevent system instability
            exclude_process_names = [
                'explorer.exe',  # Windows Explorer
                'dwm.exe',       # Desktop Window Manager
                'taskmgr.exe',   # Task Manager
                'systemsettings.exe',  # Settings
                'shellexperiencehost.exe',  # Start Menu
                'searchui.exe',  # Search
                'cortana.exe',   # Cortana
                'runtimebroker.exe',  # Runtime Broker
                'python.exe',    # Don't close ourselves
                'pythonw.exe',   # Don't close ourselves
                'g-assist-plugin-python.exe'  # Don't close the plugin
            ]
        
        exclude_lower = [name.lower() for name in exclude_process_names]
        counts = {'closed': 0, 'failed': 0, 'excluded': 0, 'whitelisted': 0}
        windows = self.enum_windows()
        
        # Define constants
        WM_CLOSE = 0x0010
        PROCESS_TERMINATE = 0x0001
        
        for window in windows:
            try:
                # Skip if in exclusion list
                if window.process_name.lower() in exclude_lower:
                    counts['excluded'] += 1
                    self.logger.info(f"Excluded {window.process_name}: {window.title}")
                    continue
                
                # Check whitelist if checker provided
                if whitelist_checker and whitelist_checker(window.process_name, window.title):
                    counts['whitelisted'] += 1
                    self.logger.info(f"Skipping whitelisted: {window.title} [{window.process_name}]")
                    continue
                
                # Skip minimized windows (already "cleared")
                if window.is_minimized:
                    continue
                
                # Try graceful close first
                self.logger.info(f"Closing {window.process_name}: {window.title}")
                
                # Send WM_CLOSE message
                result = self.user32.SendMessageW(window.hwnd, WM_CLOSE, 0, 0)
                
                # Give the window time to close gracefully
                time.sleep(0.1)
                
                # Check if window still exists
                if self.user32.IsWindow(window.hwnd):
                    if force:
                        # Force close if requested
                        self.logger.warning(f"Force closing {window.process_name}")
                        handle = self.kernel32.OpenProcess(PROCESS_TERMINATE, False, window.process_id)
                        if handle:
                            self.kernel32.TerminateProcess(handle, 0)
                            self.kernel32.CloseHandle(handle)
                            counts['closed'] += 1
                        else:
                            counts['failed'] += 1
                    else:
                        self.logger.warning(f"Window didn't close gracefully: {window.title}")
                        counts['failed'] += 1
                else:
                    counts['closed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Error closing window {window.title}: {e}")
                counts['failed'] += 1
        
        self.logger.info(f"Close windows summary: {counts}")
        return counts