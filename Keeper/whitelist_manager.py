"""Whitelist manager for Context Keeper - manages apps that should not be minimized"""
import json
import logging
from pathlib import Path
from typing import List, Set


class WhitelistManager:
    """Manages the whitelist of applications that should not be minimized.
    
    The whitelist protects important applications from being minimized
    or closed during 'clear desktop' operations. This includes:
    - NVIDIA applications (G-Assist, GeForce Experience)
    - System processes (explorer, dwm)
    - User-defined applications
    
    Whitelist is persistent across sessions and stored in:
    ~/.keeper/whitelist.json
    
    Applications can be matched by:
    - Process name (e.g., 'NVIDIA App.exe')
    - Window title pattern (e.g., 'Project G-Assist')
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.whitelist_file = Path.home() / ".keeper" / "whitelist.json"
        # Default apps that should always stay visible
        self.default_whitelist = [
            "NVIDIA App.exe",
            "nvidia app.exe",  # Case variations
            "NVIDIA GeForce Overlay.exe",
            "nvidia overlay.exe",
            "Project G-Assist",  # Window title pattern
            "G-Assist",  # Window title pattern
            "explorer.exe",  # Keep taskbar and desktop
            "dwm.exe",  # Desktop Window Manager
            "ShellExperienceHost.exe",  # Start menu
            "SearchHost.exe",  # Windows search
            "TextInputHost.exe",  # Input method
        ]
        self._ensure_whitelist()
    
    def _ensure_whitelist(self):
        """Ensure whitelist file exists with defaults"""
        self.whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.whitelist_file.exists():
            self._save_whitelist(self.default_whitelist)
    
    def _load_whitelist(self) -> List[str]:
        """Load whitelist from file"""
        try:
            with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('whitelist', self.default_whitelist)
        except Exception as e:
            self.logger.error(f"Error loading whitelist: {e}")
            return self.default_whitelist.copy()
    
    def _save_whitelist(self, whitelist: List[str]):
        """Save whitelist to file"""
        try:
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                json.dump({'whitelist': whitelist}, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving whitelist: {e}")
    
    def get_whitelist(self) -> Set[str]:
        """Get current whitelist as a set for fast lookup"""
        return set(self._load_whitelist())
    
    def add_to_whitelist(self, app_name: str) -> bool:
        """Add an application to the whitelist"""
        whitelist = self._load_whitelist()
        
        # Normalize the app name
        normalized = app_name.strip()
        
        if normalized not in whitelist:
            whitelist.append(normalized)
            self._save_whitelist(whitelist)
            self.logger.info(f"Added '{normalized}' to whitelist")
            return True
        else:
            self.logger.info(f"'{normalized}' already in whitelist")
            return False
    
    def remove_from_whitelist(self, app_name: str) -> bool:
        """Remove an application from the whitelist"""
        whitelist = self._load_whitelist()
        normalized = app_name.strip()
        
        # Don't allow removal of essential system apps
        protected_apps = ["explorer.exe", "dwm.exe"]
        if normalized.lower() in [p.lower() for p in protected_apps]:
            self.logger.warning(f"Cannot remove protected app '{normalized}' from whitelist")
            return False
        
        if normalized in whitelist:
            whitelist.remove(normalized)
            self._save_whitelist(whitelist)
            self.logger.info(f"Removed '{normalized}' from whitelist")
            return True
        else:
            self.logger.info(f"'{normalized}' not in whitelist")
            return False
    
    def is_whitelisted(self, process_name: str, window_title: str = "") -> bool:
        """Check if a process or window is whitelisted.
        
        Matching is case-insensitive and supports two modes:
        1. Process name match: Exact match for .exe files
        2. Title pattern match: Substring match for window titles
        
        Args:
            process_name: Name of the process (e.g., 'NVIDIA App.exe')
            window_title: Window title for pattern matching
            
        Returns:
            True if the window should be protected from minimize/close
        """
        whitelist = self.get_whitelist()
        
        # Check process name (case insensitive)
        process_name_lower = process_name.lower()
        for wl_item in whitelist:
            if wl_item.lower() == process_name_lower:
                return True
        
        # Check window title patterns
        if window_title:
            window_title_lower = window_title.lower()
            for wl_item in whitelist:
                if not wl_item.endswith('.exe'):  # Title patterns don't end with .exe
                    if wl_item.lower() in window_title_lower:
                        return True
        
        return False
    
    def list_whitelist(self) -> List[str]:
        """Get the current whitelist"""
        return self._load_whitelist()