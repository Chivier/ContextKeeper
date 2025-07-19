import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from browser_tab_extractor import BrowserTabExtractor


class BrowserTabSaver:
    """Save and restore browser tabs to/from JSON files.
    
    This class provides functionality to:
    - Save all open browser tabs to a JSON file
    - Restore browser tabs from a saved JSON file
    - Manage multiple saved sessions
    """
    
    def __init__(self, save_dir: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self.save_dir = save_dir or (Path.home() / ".keeper" / "browser_tabs")
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.extractor = BrowserTabExtractor()
        
    def save_all_tabs(self, session_name: Optional[str] = None) -> Dict:
        """Save all browser tabs to JSON file.
        
        Args:
            session_name: Optional name for the session. If not provided,
                        generates timestamp-based name.
                        
        Returns:
            Dict containing saved data and metadata
        """
        try:
            # Generate session name if not provided
            if not session_name:
                session_name = f"tabs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Extract tabs from all browsers
            self.logger.info(f"Extracting browser tabs for session: {session_name}")
            all_tabs = self.extractor.extract_all_browsers()
            
            # Prepare save data
            save_data = {
                "session_name": session_name,
                "timestamp": datetime.now().isoformat(),
                "browsers": all_tabs,
                "metadata": {
                    "total_tabs": sum(len(browser_data) for browser_data in all_tabs.values()),
                    "browsers_found": list(all_tabs.keys())
                }
            }
            
            # Save to JSON file
            save_path = self.save_dir / f"{session_name}.json"
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {save_data['metadata']['total_tabs']} tabs to {save_path}")
            
            return {
                "success": True,
                "session_name": session_name,
                "save_path": str(save_path),
                "metadata": save_data["metadata"]
            }
            
        except Exception as e:
            self.logger.error(f"Error saving tabs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_tabs(self, session_name: str, browser: Optional[str] = None) -> Dict:
        """Restore browser tabs from a saved JSON file.
        
        Args:
            session_name: Name of the saved session to restore
            browser: Optional specific browser to restore (chrome, edge, firefox).
                    If not specified, restores all browsers.
                    
        Returns:
            Dict containing restoration status
        """
        try:
            # Load saved data
            save_path = self.save_dir / f"{session_name}.json"
            if not save_path.exists():
                raise FileNotFoundError(f"Session '{session_name}' not found")
            
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            browsers_data = save_data.get("browsers", {})
            restored_count = 0
            
            # Restore tabs for each browser
            for browser_name, tabs_data in browsers_data.items():
                # Skip if specific browser requested and this isn't it
                if browser and browser_name != browser:
                    continue
                
                # Handle both list and dict formats
                if isinstance(tabs_data, dict) and 'tabs' in tabs_data:
                    tabs = tabs_data['tabs']
                else:
                    tabs = tabs_data if isinstance(tabs_data, list) else []
                
                if not tabs:
                    continue
                
                self.logger.info(f"Restoring {len(tabs)} tabs for {browser_name}")
                
                # Open browser with tabs
                if browser_name == "chrome":
                    self._open_chrome_tabs(tabs)
                elif browser_name == "edge":
                    self._open_edge_tabs(tabs)
                elif browser_name == "firefox":
                    self._open_firefox_tabs(tabs)
                
                restored_count += len(tabs)
            
            return {
                "success": True,
                "restored_tabs": restored_count,
                "session_name": session_name,
                "timestamp": save_data.get("timestamp")
            }
            
        except Exception as e:
            self.logger.error(f"Error restoring tabs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _open_chrome_tabs(self, tabs: List[Dict]):
        """Open Chrome with specified tabs."""
        urls = [tab.get('url', '') for tab in tabs if tab.get('url', '').startswith('http')]
        if urls:
            # Open Chrome with all URLs
            cmd = f'start chrome {" ".join(f'"{url}"' for url in urls)}'
            os.system(cmd)
    
    def _open_edge_tabs(self, tabs: List[Dict]):
        """Open Edge with specified tabs."""
        urls = [tab.get('url', '') for tab in tabs if tab.get('url', '').startswith('http')]
        if urls:
            # Open Edge with all URLs
            cmd = f'start msedge {" ".join(f'"{url}"' for url in urls)}'
            os.system(cmd)
    
    def _open_firefox_tabs(self, tabs: List[Dict]):
        """Open Firefox with specified tabs."""
        urls = [tab.get('url', '') for tab in tabs if tab.get('url', '').startswith('http')]
        if urls:
            # Open Firefox with all URLs
            cmd = f'start firefox {" ".join(f'"{url}"' for url in urls)}'
            os.system(cmd)
    
    def list_saved_sessions(self) -> List[Dict]:
        """List all saved tab sessions.
        
        Returns:
            List of session information dictionaries
        """
        sessions = []
        
        for json_file in self.save_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                sessions.append({
                    "session_name": data.get("session_name", json_file.stem),
                    "timestamp": data.get("timestamp"),
                    "total_tabs": data.get("metadata", {}).get("total_tabs", 0),
                    "browsers": data.get("metadata", {}).get("browsers_found", []),
                    "file_path": str(json_file)
                })
            except Exception as e:
                self.logger.warning(f"Error reading session file {json_file}: {e}")
        
        # Sort by timestamp (newest first)
        sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return sessions
    
    def delete_session(self, session_name: str) -> bool:
        """Delete a saved session.
        
        Args:
            session_name: Name of the session to delete
            
        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            save_path = self.save_dir / f"{session_name}.json"
            if save_path.exists():
                save_path.unlink()
                self.logger.info(f"Deleted session: {session_name}")
                return True
            else:
                self.logger.warning(f"Session not found: {session_name}")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            return False
    
    def get_session_details(self, session_name: str) -> Optional[Dict]:
        """Get detailed information about a saved session.
        
        Args:
            session_name: Name of the session
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            save_path = self.save_dir / f"{session_name}.json"
            if not save_path.exists():
                return None
            
            with open(save_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading session details: {e}")
            return None