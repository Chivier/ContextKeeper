import json
import logging
import os
import requests
import socket
import subprocess
import sqlite3
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import base64
from urllib.parse import urlparse


class BrowserTabExtractor:
    """Extract browser tabs using browser debugging protocols.
    
    This class provides cross-browser tab extraction without requiring
    browser extensions. It uses:
    - Chrome/Edge: Chrome DevTools Protocol via debugging port
    - Firefox: Session store files (recovery.jsonlz4)
    
    Features:
    - Tab URLs and titles
    - Active tab tracking
    - Favicon extraction (base64)
    - Tab group detection (limited)
    
    Note: Browsers must be running with debugging enabled for full access.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def extract_all_browsers(self) -> Dict[str, List[Dict]]:
        """Extract tabs from all supported browsers"""
        results = {}
        
        # Try Chrome/Edge
        chrome_tabs = self.extract_chrome_tabs()
        if chrome_tabs:
            results['chrome'] = chrome_tabs
            
        edge_tabs = self.extract_edge_tabs()
        if edge_tabs:
            results['edge'] = edge_tabs
            
        # Try Firefox
        firefox_tabs = self.extract_firefox_tabs()
        if firefox_tabs:
            results['firefox'] = firefox_tabs
            
        return results
    
    def extract_chrome_tabs(self) -> List[Dict]:
        """Extract Chrome tabs using debugging protocol"""
        return self._extract_chromium_tabs('chrome')
    
    def extract_edge_tabs(self) -> List[Dict]:
        """Extract Edge tabs using multiple methods in order of preference:
        1. Debugging protocol (if available)
        2. Session/recovery files
        3. UI automation (fallback)
        """
        # First try debugging protocol
        tabs = self._extract_chromium_tabs('msedge')
        if tabs:
            return tabs
            
        # Try session files as second option
        tabs = self._extract_edge_session_tabs()
        if tabs:
            return tabs
            
        # UI automation will be tried as last resort inside _extract_chromium_tabs
        return []
    
    def _extract_chromium_tabs(self, browser_name: str) -> List[Dict]:
        """Extract tabs from Chromium-based browsers (Chrome, Edge).
        
        Process:
        1. Find the browser's debugging port (usually 9222-9225)
        2. Query /json endpoint for all tabs
        3. Filter for actual page tabs (not extensions/devtools)
        4. Extract URL, title, favicon, and active state
        
        Args:
            browser_name: 'chrome' or 'msedge'
            
        Returns:
            List of tab dictionaries or dict with 'tabs' and 'activeIndex'
        """
        try:
            # Find Chrome/Edge debugging port
            debug_port = self._find_chromium_debug_port(browser_name)
            if not debug_port:
                self.logger.warning(f"No {browser_name} debugging port found, trying UI automation")
                # Try UI automation as fallback
                return self._extract_chromium_tabs_ui_automation(browser_name)
            
            # Get tab list
            response = requests.get(f'http://localhost:{debug_port}/json', timeout=5)
            tabs_data = response.json()
            
            tabs = []
            active_index = -1
            
            for idx, tab in enumerate(tabs_data):
                if tab.get('type') == 'page':
                    tab_info = {
                        'url': tab.get('url', ''),
                        'title': tab.get('title', ''),
                        'favicon': self._get_favicon_base64(tab.get('favIconUrl', '')),
                        'active': tab.get('active', False),
                        'index': idx
                    }
                    
                    # Try to get tab group info from title or other metadata
                    # Chrome doesn't expose groups via debugging API directly
                    # This would need Chrome extension or UI automation for full support
                    tab_info['groupId'] = None
                    tab_info['groupName'] = None
                    
                    if tab.get('active', False):
                        active_index = idx
                    
                    tabs.append(tab_info)
            
            # Add active tab index to result
            if tabs and active_index >= 0:
                return {'tabs': tabs, 'activeIndex': active_index}
            
            return tabs
            
        except Exception as e:
            self.logger.error(f"Error extracting {browser_name} tabs: {e}")
            return []
    
    def _extract_chromium_tabs_ui_automation(self, browser_name: str) -> List[Dict]:
        """Extract tabs using UI automation as fallback when debugging port is not available.
        
        This method uses pywinauto to interact with the browser UI and extract tab information.
        It's slower and less reliable than the debugging protocol but works without special flags.
        
        Args:
            browser_name: 'chrome' or 'msedge'
            
        Returns:
            List of tab dictionaries
        """
        try:
            import pywinauto
            from pywinauto import Application
            import time
            
            # Find browser windows
            windows = []
            process_name = 'chrome.exe' if browser_name == 'chrome' else 'msedge.exe'
            
            # Get all browser windows
            import psutil
            import win32gui
            import win32process
            
            def enum_window_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        proc = psutil.Process(pid)
                        if proc.name().lower() == process_name.lower():
                            window_text = win32gui.GetWindowText(hwnd)
                            if window_text and ('Microsoft​ Edge' in window_text or 'Google Chrome' in window_text or 'Edge' in window_text):
                                windows.append((hwnd, window_text))
                    except:
                        pass
                return True
            
            win32gui.EnumWindows(enum_window_callback, windows)
            
            if not windows:
                self.logger.warning(f"No {browser_name} windows found for UI automation")
                return []
            
            tabs = []
            # For each browser window, extract its title (contains current tab info)
            for hwnd, window_title in windows:
                # Edge window title format: "Page Title - Microsoft​ Edge"
                # Chrome window title format: "Page Title - Google Chrome"
                if ' - Microsoft​ Edge' in window_title:
                    title = window_title.replace(' - Microsoft​ Edge', '').strip()
                elif ' - Microsoft Edge' in window_title:  # Sometimes without special character
                    title = window_title.replace(' - Microsoft Edge', '').strip()
                elif ' - Google Chrome' in window_title:
                    title = window_title.replace(' - Google Chrome', '').strip()
                else:
                    title = window_title
                
                # Try to extract URL using accessibility APIs
                try:
                    app = Application(backend='uia').connect(handle=hwnd)
                    window = app.window(handle=hwnd)
                    
                    # Try to find address bar and get URL
                    url = ''
                    try:
                        # For Edge/Chrome, the address bar is usually named "Address and search bar"
                        address_bar = window.child_window(title_re=".*Address.*", control_type="Edit")
                        if address_bar.exists():
                            url = address_bar.get_value()
                    except:
                        pass
                    
                    # If we have at least a title, add it as a tab
                    if title:
                        tabs.append({
                            'url': url or 'unknown',
                            'title': title,
                            'favicon': '',
                            'active': True,  # We can't determine which tab is active easily
                            'window_id': hwnd
                        })
                    
                except Exception as e:
                    # Fallback: just use window title
                    if title:
                        tabs.append({
                            'url': 'unknown',
                            'title': title,
                            'favicon': '',
                            'active': True,
                            'window_id': hwnd
                        })
            
            self.logger.info(f"Extracted {len(tabs)} tabs from {browser_name} using UI automation")
            return tabs
            
        except Exception as e:
            self.logger.error(f"Error in UI automation for {browser_name}: {e}")
            return []
    
    def _extract_edge_session_tabs(self) -> List[Dict]:
        """Extract Edge tabs from session/recovery files.
        
        Edge stores session data in various locations that we can parse
        to get tab information even without debugging access.
        
        Returns:
            List of tab dictionaries
        """
        try:
            import json
            import os
            
            # Edge user data locations
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                return []
                
            edge_user_data = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data')
            if not os.path.exists(edge_user_data):
                return []
            
            all_tabs = []
            
            # Check each profile directory
            for item in os.listdir(edge_user_data):
                profile_path = os.path.join(edge_user_data, item)
                if os.path.isdir(profile_path) and (item == 'Default' or item.startswith('Profile')):
                    # Look for session files
                    session_files = [
                        'Current Session',
                        'Last Session',
                        'Current Tabs',
                        'Last Tabs'
                    ]
                    
                    for session_file in session_files:
                        session_path = os.path.join(profile_path, session_file)
                        if os.path.exists(session_path):
                            tabs = self._parse_edge_session_file(session_path)
                            if tabs:
                                all_tabs.extend(tabs)
                                break  # Use first valid session file found
                    
                    # Also check Sessions folder
                    sessions_folder = os.path.join(profile_path, 'Sessions')
                    if os.path.exists(sessions_folder):
                        # Get most recent session file
                        session_files = [f for f in os.listdir(sessions_folder) if f.startswith('Session_')]
                        if session_files:
                            session_files.sort(reverse=True)  # Most recent first
                            session_path = os.path.join(sessions_folder, session_files[0])
                            tabs = self._parse_edge_session_file(session_path)
                            if tabs:
                                all_tabs.extend(tabs)
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_tabs = []
            for tab in all_tabs:
                if tab['url'] not in seen_urls:
                    seen_urls.add(tab['url'])
                    unique_tabs.append(tab)
            
            self.logger.info(f"Extracted {len(unique_tabs)} unique Edge tabs from session files")
            return unique_tabs
            
        except Exception as e:
            self.logger.error(f"Error extracting Edge session tabs: {e}")
            return []
    
    def _parse_edge_session_file(self, file_path: str) -> List[Dict]:
        """Parse an Edge session file to extract tab information.
        
        Edge session files use a binary SNSS format that contains URLs and titles.
        This method attempts to extract readable information from these files.
        
        Args:
            file_path: Path to the session file
            
        Returns:
            List of tab dictionaries
        """
        tabs = []
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Convert to string, ignoring decode errors
            text_content = content.decode('utf-8', errors='ignore')
            
            # Look for URLs using various patterns
            import re
            
            # Pattern for http/https URLs
            url_pattern = re.compile(r'https?://[^\s\x00-\x1f\x7f-\x9f<>"{}|\\^`\[\]]+')
            urls = url_pattern.findall(text_content)
            
            # Try to find associated titles (usually near URLs in the file)
            for url in urls:
                if url.startswith('http'):
                    # Skip internal Chrome/Edge URLs
                    if any(skip in url for skip in ['edge://', 'chrome://', 'about:', 'data:', 'blob:']):
                        continue
                    
                    # Create tab entry
                    tab = {
                        'url': url,
                        'title': self._extract_title_near_url(text_content, url) or url,
                        'favicon': '',
                        'active': False
                    }
                    tabs.append(tab)
            
            return tabs
            
        except Exception as e:
            self.logger.error(f"Error parsing Edge session file {file_path}: {e}")
            return []
    
    def _extract_title_near_url(self, content: str, url: str) -> Optional[str]:
        """Try to extract a title near a URL in session file content.
        
        This is a heuristic approach that looks for readable text near the URL.
        
        Args:
            content: The file content as string
            url: The URL to find title for
            
        Returns:
            Title if found, None otherwise
        """
        try:
            # Find URL position
            pos = content.find(url)
            if pos == -1:
                return None
            
            # Look for title in surrounding text (before URL is common)
            start = max(0, pos - 500)
            end = pos
            
            surrounding = content[start:end]
            
            # Extract readable strings (at least 3 chars, no control chars)
            import re
            readable_pattern = re.compile(r'[^\x00-\x1f\x7f-\x9f]{3,}')
            readable_strings = readable_pattern.findall(surrounding)
            
            # Get the last few readable strings before URL (likely title)
            if readable_strings:
                # Filter out URLs and very long strings
                candidates = [s for s in readable_strings[-5:] 
                             if not s.startswith('http') and len(s) < 200]
                if candidates:
                    return candidates[-1].strip()
            
            return None
            
        except:
            return None
    
    def _find_chromium_debug_port(self, browser_name: str) -> Optional[int]:
        """Find the debugging port for Chrome/Edge.
        
        Strategy:
        1. Check common ports (9222-9225) for active debug interface
        2. Scan process command lines for --remote-debugging-port
        3. Verify port responds to /json/version endpoint
        
        Most browsers don't enable debugging by default. Users may need
        to launch with: --remote-debugging-port=9222
        
        Returns:
            Port number if found, None otherwise
        """
        # Common debugging ports
        common_ports = [9222, 9223, 9224, 9225]
        
        for port in common_ports:
            if self._is_port_open('localhost', port):
                try:
                    response = requests.get(f'http://localhost:{port}/json/version', timeout=1)
                    if response.status_code == 200:
                        return port
                except:
                    pass
        
        # Try to find from process command line
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if browser_name in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    for arg in cmdline:
                        if '--remote-debugging-port=' in arg:
                            port = int(arg.split('=')[1])
                            if self._is_port_open('localhost', port):
                                return port
            except:
                continue
                
        return None
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    
    def extract_firefox_tabs(self) -> List[Dict]:
        """Extract Firefox tabs from session store"""
        try:
            # Find Firefox profile
            profile_path = self._find_firefox_profile()
            if not profile_path:
                return []
            
            # Look for session files
            session_files = [
                'sessionstore-backups/recovery.jsonlz4',
                'sessionstore-backups/recovery.baklz4',
                'sessionstore.jsonlz4'
            ]
            
            for session_file in session_files:
                full_path = os.path.join(profile_path, session_file)
                if os.path.exists(full_path):
                    session_data = self._read_firefox_session(full_path)
                    if session_data:
                        return self._parse_firefox_session(session_data)
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error extracting Firefox tabs: {e}")
            return []
    
    def _find_firefox_profile(self) -> Optional[str]:
        """Find the default Firefox profile path"""
        if os.name == 'nt':  # Windows
            app_data = os.environ.get('APPDATA')
            if app_data:
                profiles_path = os.path.join(app_data, 'Mozilla', 'Firefox', 'Profiles')
                if os.path.exists(profiles_path):
                    # Find default profile
                    for profile in os.listdir(profiles_path):
                        if '.default' in profile or profile.endswith('.default-release'):
                            return os.path.join(profiles_path, profile)
        
        return None
    
    def _read_firefox_session(self, file_path: str) -> Optional[str]:
        """Read Firefox session file (handles jsonlz4 format)"""
        try:
            with open(file_path, 'rb') as f:
                # Skip mozLz40 header (8 bytes)
                f.read(8)
                
                # Try to decompress with lz4
                try:
                    import lz4.block
                    compressed = f.read()
                    decompressed = lz4.block.decompress(compressed)
                    return decompressed.decode('utf-8')
                except ImportError:
                    # If lz4 not available, try alternative method
                    self.logger.warning("lz4 module not available, Firefox tabs extraction limited")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error reading Firefox session: {e}")
            return None
    
    def _parse_firefox_session(self, session_data: str) -> List[Dict]:
        """Parse Firefox session data to extract tabs"""
        try:
            data = json.loads(session_data)
            tabs = []
            
            for window in data.get('windows', []):
                for tab in window.get('tabs', []):
                    entries = tab.get('entries', [])
                    if entries:
                        # Get the current entry
                        index = tab.get('index', 1) - 1
                        if 0 <= index < len(entries):
                            entry = entries[index]
                            tabs.append({
                                'url': entry.get('url', ''),
                                'title': entry.get('title', ''),
                                'favicon': self._get_favicon_base64(entry.get('favIconUrl', '')),
                                'active': tab.get('selected', False)
                            })
            
            return tabs
            
        except Exception as e:
            self.logger.error(f"Error parsing Firefox session: {e}")
            return []
    
    def _get_favicon_base64(self, favicon_url: str) -> str:
        """Get favicon as base64 encoded string"""
        if not favicon_url or favicon_url.startswith('data:'):
            return favicon_url
        
        try:
            response = requests.get(favicon_url, timeout=2)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/x-icon')
                base64_data = base64.b64encode(response.content).decode('utf-8')
                return f"data:{content_type};base64,{base64_data}"
        except:
            pass
            
        return ""
    
    def get_browser_bookmarks(self, browser: str) -> List[Dict]:
        """Get bookmarks as fallback when tabs cannot be accessed"""
        if browser.lower() in ['chrome', 'edge']:
            return self._get_chromium_bookmarks(browser)
        elif browser.lower() == 'firefox':
            return self._get_firefox_bookmarks()
        return []
    
    def _get_chromium_bookmarks(self, browser: str) -> List[Dict]:
        """Get Chrome/Edge bookmarks"""
        try:
            if browser.lower() == 'chrome':
                local_app_data = os.environ.get('LOCALAPPDATA')
                bookmarks_path = os.path.join(local_app_data, 'Google', 'Chrome', 'User Data', 'Default', 'Bookmarks')
            else:  # Edge
                local_app_data = os.environ.get('LOCALAPPDATA')
                bookmarks_path = os.path.join(local_app_data, 'Microsoft', 'Edge', 'User Data', 'Default', 'Bookmarks')
            
            if os.path.exists(bookmarks_path):
                with open(bookmarks_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                bookmarks = []
                # Parse bookmark tree
                for root_name, root_data in data.get('roots', {}).items():
                    if isinstance(root_data, dict) and 'children' in root_data:
                        self._parse_bookmark_folder(root_data, bookmarks)
                        
                return bookmarks
                
        except Exception as e:
            self.logger.error(f"Error reading {browser} bookmarks: {e}")
            
        return []
    
    def _parse_bookmark_folder(self, folder: Dict, bookmarks: List[Dict]) -> None:
        """Recursively parse bookmark folders"""
        for child in folder.get('children', []):
            if child.get('type') == 'url':
                bookmarks.append({
                    'url': child.get('url', ''),
                    'title': child.get('name', ''),
                    'date_added': child.get('date_added', '')
                })
            elif child.get('type') == 'folder':
                self._parse_bookmark_folder(child, bookmarks)
    
    def _get_firefox_bookmarks(self) -> List[Dict]:
        """Get Firefox bookmarks from places.sqlite"""
        try:
            profile_path = self._find_firefox_profile()
            if not profile_path:
                return []
                
            places_db = os.path.join(profile_path, 'places.sqlite')
            if not os.path.exists(places_db):
                return []
            
            # Copy database to temp location to avoid locks
            temp_db = os.path.join(tempfile.gettempdir(), 'places_temp.sqlite')
            shutil.copy2(places_db, temp_db)
            
            bookmarks = []
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Query bookmarks
            cursor.execute("""
                SELECT moz_places.url, moz_bookmarks.title
                FROM moz_bookmarks
                JOIN moz_places ON moz_bookmarks.fk = moz_places.id
                WHERE moz_bookmarks.type = 1
            """)
            
            for row in cursor.fetchall():
                bookmarks.append({
                    'url': row[0],
                    'title': row[1] or ''
                })
            
            conn.close()
            os.remove(temp_db)
            
            return bookmarks
            
        except Exception as e:
            self.logger.error(f"Error reading Firefox bookmarks: {e}")
            return []