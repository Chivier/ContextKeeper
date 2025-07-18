import json
import logging
import os
import socket
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil


class FastBrowserTabExtractor:
    """Optimized browser tab extractor with timeouts and parallel processing"""
    
    def __init__(self, timeout=2.0):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self._browser_ports_cache = {}
        
    def extract_all_browsers(self) -> Dict[str, List[Dict]]:
        """Extract tabs from all browsers in parallel"""
        results = {}
        
        # Use thread pool for parallel extraction
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.extract_chrome_tabs): 'chrome',
                executor.submit(self.extract_edge_tabs): 'edge',
                executor.submit(self.extract_firefox_tabs): 'firefox'
            }
            
            for future in as_completed(futures, timeout=self.timeout):
                browser = futures[future]
                try:
                    tabs = future.result(timeout=0.1)
                    if tabs:
                        results[browser] = tabs
                except Exception as e:
                    self.logger.warning(f"Failed to extract {browser} tabs: {e}")
                    
        return results
    
    def extract_chrome_tabs(self) -> List[Dict]:
        """Extract Chrome tabs - fast version"""
        return self._extract_chromium_tabs_fast('chrome')
    
    def extract_edge_tabs(self) -> List[Dict]:
        """Extract Edge tabs - fast version with fallback"""
        # First try fast method
        tabs = self._extract_chromium_tabs_fast('msedge')
        if tabs:
            return tabs
            
        # If no debugging port, try importing full extractor for fallback
        try:
            from browser_tab_extractor import BrowserTabExtractor
            extractor = BrowserTabExtractor()
            # This will try session files and UI automation
            return extractor.extract_edge_tabs()
        except Exception as e:
            self.logger.debug(f"Fallback Edge extraction failed: {e}")
            return []
    
    def _extract_chromium_tabs_fast(self, browser_name: str) -> List[Dict]:
        """Fast extraction without favicons or heavy operations"""
        try:
            # Check cache first
            if browser_name in self._browser_ports_cache:
                port = self._browser_ports_cache[browser_name]
                if self._is_port_open_fast('localhost', port):
                    return self._get_tabs_from_port(port)
            
            # Find port quickly
            port = self._find_chromium_port_fast(browser_name)
            if not port:
                return []
                
            self._browser_ports_cache[browser_name] = port
            return self._get_tabs_from_port(port)
            
        except Exception as e:
            self.logger.debug(f"Error extracting {browser_name} tabs: {e}")
            return []
    
    def _find_chromium_port_fast(self, browser_name: str) -> Optional[int]:
        """Quickly find browser debug port"""
        # First try common ports
        common_ports = [9222, 9223, 9224, 9225]
        
        # Check ports in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._check_port_browser, port): port 
                      for port in common_ports}
            
            for future in as_completed(futures, timeout=0.5):
                port = futures[future]
                try:
                    if future.result():
                        return port
                except:
                    pass
        
        # Quick process scan (limit time)
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                if browser_name in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    for arg in cmdline:
                        if '--remote-debugging-port=' in arg:
                            try:
                                port = int(arg.split('=')[1])
                                return port
                            except:
                                pass
        except:
            pass
            
        return None
    
    def _check_port_browser(self, port: int) -> bool:
        """Check if port has browser debug interface"""
        try:
            import urllib.request
            req = urllib.request.Request(f'http://localhost:{port}/json/version')
            with urllib.request.urlopen(req, timeout=0.3) as response:
                return response.status == 200
        except:
            return False
    
    def _is_port_open_fast(self, host: str, port: int) -> bool:
        """Fast port check"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    
    def _get_tabs_from_port(self, port: int) -> List[Dict]:
        """Get tabs from debug port without fetching favicons"""
        try:
            import urllib.request
            import json
            
            req = urllib.request.Request(f'http://localhost:{port}/json')
            with urllib.request.urlopen(req, timeout=0.5) as response:
                tabs_data = json.loads(response.read().decode())
            
            tabs = []
            active_index = -1
            
            for idx, tab in enumerate(tabs_data):
                if tab.get('type') == 'page':
                    tab_info = {
                        'url': tab.get('url', ''),
                        'title': tab.get('title', ''),
                        'favicon': '',  # Skip favicon fetching
                        'active': tab.get('active', False),
                        'index': idx
                    }
                    
                    if tab.get('active', False):
                        active_index = idx
                    
                    tabs.append(tab_info)
            
            if tabs and active_index >= 0:
                return {'tabs': tabs, 'activeIndex': active_index}
            
            return tabs
            
        except Exception as e:
            self.logger.debug(f"Error getting tabs from port {port}: {e}")
            return []
    
    def extract_firefox_tabs(self) -> List[Dict]:
        """Fast Firefox extraction - return empty for now"""
        # Firefox session extraction is complex and slow
        # Skip it for quick saves
        return []