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
    """Extract browser tabs using various methods without requiring extensions"""
    
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
        """Extract Edge tabs using debugging protocol"""
        return self._extract_chromium_tabs('msedge')
    
    def _extract_chromium_tabs(self, browser_name: str) -> List[Dict]:
        """Extract tabs from Chromium-based browsers"""
        try:
            # Find Chrome/Edge debugging port
            debug_port = self._find_chromium_debug_port(browser_name)
            if not debug_port:
                self.logger.warning(f"No {browser_name} debugging port found")
                return []
            
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
    
    def _find_chromium_debug_port(self, browser_name: str) -> Optional[int]:
        """Find the debugging port for Chrome/Edge"""
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