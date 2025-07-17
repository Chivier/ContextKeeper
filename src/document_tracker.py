"""
Document status tracking for Office, Notion, Obsidian, OneNote, etc.
"""

import os
import json
import psutil
import logging
from typing import Dict, List, Optional
from pathlib import Path
import win32com.client
import win32gui
import win32process


class DocumentTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_document_states(self) -> List[Dict]:
        """Get status of all open documents"""
        states = []
        
        # Check Office documents
        states.extend(self._get_office_documents())
        
        # Check note-taking apps
        states.extend(self._get_notion_state())
        states.extend(self._get_obsidian_state())
        states.extend(self._get_onenote_state())
        
        return states
    
    def _get_office_documents(self) -> List[Dict]:
        """Get open Office documents with save status"""
        documents = []
        
        # Check Word documents
        try:
            word = win32com.client.Dispatch("Word.Application")
            for doc in word.Documents:
                documents.append({
                    "type": "word",
                    "processName": "WINWORD.EXE",
                    "filePath": doc.FullName if doc.Path else None,
                    "fileName": doc.Name,
                    "saved": doc.Saved,
                    "readOnly": doc.ReadOnly,
                    "window": self._get_window_info("WINWORD.EXE", doc.Name)
                })
        except Exception as e:
            self.logger.debug(f"No Word documents open or Word not installed: {e}")
        
        # Check Excel documents
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            for wb in excel.Workbooks:
                documents.append({
                    "type": "excel",
                    "processName": "EXCEL.EXE",
                    "filePath": wb.FullName if wb.Path else None,
                    "fileName": wb.Name,
                    "saved": wb.Saved,
                    "readOnly": wb.ReadOnly,
                    "window": self._get_window_info("EXCEL.EXE", wb.Name)
                })
        except Exception as e:
            self.logger.debug(f"No Excel documents open or Excel not installed: {e}")
            
        # Check PowerPoint documents
        try:
            ppt = win32com.client.Dispatch("PowerPoint.Application")
            for pres in ppt.Presentations:
                documents.append({
                    "type": "powerpoint",
                    "processName": "POWERPNT.EXE",
                    "filePath": pres.FullName if pres.Path else None,
                    "fileName": pres.Name,
                    "saved": pres.Saved,
                    "readOnly": pres.ReadOnly,
                    "window": self._get_window_info("POWERPNT.EXE", pres.Name)
                })
        except Exception as e:
            self.logger.debug(f"No PowerPoint documents open or PowerPoint not installed: {e}")
            
        return documents
    
    def _get_notion_state(self) -> List[Dict]:
        """Get Notion state"""
        states = []
        
        # Check if Notion is running
        notion_windows = self._find_windows_by_process("Notion.exe")
        
        for hwnd, title in notion_windows:
            # Try to extract page info from window title
            page_url = None
            if " - Notion" in title:
                page_name = title.replace(" - Notion", "").strip()
            else:
                page_name = title
                
            states.append({
                "type": "notion",
                "processName": "Notion.exe",
                "pageTitle": page_name,
                "pageUrl": page_url,  # Would need browser integration for actual URL
                "window": self._get_window_rect(hwnd)
            })
            
        return states
    
    def _get_obsidian_state(self) -> List[Dict]:
        """Get Obsidian vault and open files"""
        states = []
        
        # Check if Obsidian is running
        obsidian_windows = self._find_windows_by_process("Obsidian.exe")
        
        for hwnd, title in obsidian_windows:
            # Extract vault and file info from title
            vault_name = None
            file_name = None
            
            if " - Obsidian" in title:
                parts = title.replace(" - Obsidian", "").strip()
                if " - " in parts:
                    file_name, vault_name = parts.rsplit(" - ", 1)
                else:
                    vault_name = parts
                    
            # Try to find vault path
            vault_path = self._find_obsidian_vault_path(vault_name)
            
            states.append({
                "type": "obsidian",
                "processName": "Obsidian.exe",
                "vaultName": vault_name,
                "vaultPath": vault_path,
                "openFile": file_name,
                "window": self._get_window_rect(hwnd)
            })
            
        return states
    
    def _get_onenote_state(self) -> List[Dict]:
        """Get OneNote notebook state"""
        states = []
        
        # Check both desktop and UWP versions
        onenote_processes = ["ONENOTE.EXE", "ApplicationFrameHost.exe"]
        
        for process_name in onenote_processes:
            windows = self._find_windows_by_process(process_name)
            
            for hwnd, title in windows:
                if "OneNote" in title:
                    # Extract notebook info from title
                    notebook_name = title.replace("OneNote", "").replace("-", "").strip()
                    
                    states.append({
                        "type": "onenote",
                        "processName": process_name,
                        "notebookName": notebook_name,
                        "window": self._get_window_rect(hwnd)
                    })
                    
        return states
    
    def _find_windows_by_process(self, process_name: str) -> List[tuple]:
        """Find all windows belonging to a process"""
        windows = []
        
        def enum_window_callback(hwnd, param):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    if process.name().lower() == process_name.lower():
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            windows.append((hwnd, title))
                except:
                    pass
            return True
            
        win32gui.EnumWindows(enum_window_callback, None)
        return windows
    
    def _get_window_info(self, process_name: str, doc_name: str) -> Optional[Dict]:
        """Get window info for a document"""
        windows = self._find_windows_by_process(process_name)
        
        for hwnd, title in windows:
            if doc_name in title:
                return self._get_window_rect(hwnd)
                
        return None
    
    def _get_window_rect(self, hwnd: int) -> Dict:
        """Get window position and size"""
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return {
                "x": rect[0],
                "y": rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
                "state": "normal"  # Could be enhanced with maximize/minimize detection
            }
        except:
            return {"x": 0, "y": 0, "width": 0, "height": 0, "state": "unknown"}
    
    def _find_obsidian_vault_path(self, vault_name: str) -> Optional[str]:
        """Try to find Obsidian vault path"""
        if not vault_name:
            return None
            
        # Common Obsidian vault locations
        possible_locations = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Documents" / "Obsidian Vault",
            Path.home() / "Documents" / vault_name,
            Path.home() / "Obsidian",
            Path.home() / vault_name,
        ]
        
        for location in possible_locations:
            if location.exists() and location.is_dir():
                # Check if it's an Obsidian vault (has .obsidian folder)
                if (location / ".obsidian").exists():
                    return str(location)
                    
        return None
    
    def check_unsaved_documents(self) -> List[Dict]:
        """Check for any unsaved documents"""
        unsaved = []
        
        documents = self._get_office_documents()
        for doc in documents:
            if not doc.get("saved", True):
                unsaved.append({
                    "type": doc["type"],
                    "fileName": doc["fileName"],
                    "filePath": doc.get("filePath")
                })
                
        return unsaved
    
    def restore_document(self, document_data: Dict) -> bool:
        """Restore a document"""
        doc_type = document_data.get("type")
        file_path = document_data.get("filePath")
        
        if not file_path:
            self.logger.warning(f"No file path for document: {document_data}")
            return False
            
        try:
            if doc_type == "word":
                os.startfile(file_path)
            elif doc_type == "excel":
                os.startfile(file_path)
            elif doc_type == "powerpoint":
                os.startfile(file_path)
            elif doc_type == "obsidian":
                # Open Obsidian with vault
                vault_path = document_data.get("vaultPath")
                if vault_path:
                    os.startfile(f"obsidian://open?vault={vault_path}")
            elif doc_type == "notion":
                # Open Notion (would need page URL for specific page)
                os.startfile("notion://")
            elif doc_type == "onenote":
                # Open OneNote
                os.startfile("onenote:")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore document: {e}")
            return False