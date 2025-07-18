import ctypes
import ctypes.wintypes
import logging
import psutil
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass


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


class WindowsContextManager:
    """Manages Windows-specific context operations using Windows API"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
    def enum_windows(self) -> List[WindowInfo]:
        """Enumerate all windows and return their information"""
        windows = []
        
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
                
                # Get window info
                window_info = self._get_window_info(hwnd)
                if window_info:
                    windows.append(window_info)
                    
            except Exception as e:
                self.logger.warning(f"Error processing window {hwnd}: {e}")
                
            return True
        
        # Create callback and enumerate windows
        callback = EnumWindowsProc(enum_windows_callback)
        self.user32.EnumWindows(callback, 0)
        
        return windows
    
    def _get_window_title(self, hwnd: int) -> str:
        """Get window title"""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    
    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
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
                process = psutil.Process(process_id.value)
                process_name = process.name()
            except:
                process_name = "Unknown"
            
            # Get window state
            placement = ctypes.wintypes.WINDOWPLACEMENT()
            placement.length = ctypes.sizeof(placement)
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
                is_visible=is_visible
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
    
    def minimize_all_windows(self) -> int:
        """Minimize all visible windows"""
        count = 0
        windows = self.enum_windows()
        
        for window in windows:
            if window.is_visible and not window.is_minimized:
                try:
                    self.user32.ShowWindow(window.hwnd, 6)  # SW_MINIMIZE
                    count += 1
                except:
                    pass
                    
        return count
    
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
    
    def close_all_windows(self, exclude_process_names: List[str] = None, force: bool = False) -> Dict[str, int]:
        """Close all visible windows with safety checks
        
        Args:
            exclude_process_names: List of process names to exclude from closing (e.g., ['explorer.exe'])
            force: If True, use TerminateProcess for unresponsive windows (dangerous!)
            
        Returns:
            Dict with counts: {'closed': n, 'failed': n, 'excluded': n}
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
        counts = {'closed': 0, 'failed': 0, 'excluded': 0}
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