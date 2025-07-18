import json
import logging
import os
import psutil
import glob
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import sqlite3
import tempfile
import shutil


@dataclass
class IDEState:
    """State information for an IDE"""
    type: str  # vscode, pycharm, idea, etc.
    process_name: str
    project_path: Optional[str]
    open_files: List[str]
    window_title: str
    recent_projects: List[str]
    window_hwnd: Optional[int] = None


class IDETracker:
    """Track state of various IDEs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_all_ide_states(self) -> List[IDEState]:
        """Get state information for all running IDEs"""
        ide_states = []
        
        # Check for each IDE type
        ide_states.extend(self._get_vscode_states())
        ide_states.extend(self._get_jetbrains_states())
        ide_states.extend(self._get_sublime_states())
        ide_states.extend(self._get_notepad_plus_states())
        
        return ide_states
    
    def _get_vscode_states(self) -> List[IDEState]:
        """Get VSCode/Cursor state information"""
        states = []
        
        # Process names to check
        vscode_processes = ['Code.exe', 'cursor.exe', 'code-insiders.exe']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] in vscode_processes:
                    # Extract workspace from command line
                    cmdline = proc.info.get('cmdline', [])
                    workspace_path = None
                    
                    for i, arg in enumerate(cmdline):
                        if arg in ['--folder-uri', '--file-uri']:
                            if i + 1 < len(cmdline):
                                uri = cmdline[i + 1]
                                # Convert file URI to path
                                if uri.startswith('file:///'):
                                    workspace_path = uri.replace('file:///', '').replace('/', '\\')
                        elif os.path.exists(arg) and os.path.isdir(arg):
                            workspace_path = arg
                            
                    # Get open files from VSCode workspace storage
                    open_files = self._get_vscode_open_files(proc.info['name'])
                    
                    # Get recent projects
                    recent_projects = self._get_vscode_recent_projects()
                    
                    state = IDEState(
                        type='vscode',
                        process_name=proc.info['name'],
                        project_path=workspace_path,
                        open_files=open_files,
                        window_title=f"VSCode - {os.path.basename(workspace_path) if workspace_path else 'No Folder'}",
                        recent_projects=recent_projects,
                        window_hwnd=self._get_process_main_window(proc.pid)
                    )
                    states.append(state)
                    
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
                
        return states
    
    def _get_vscode_open_files(self, process_name: str) -> List[str]:
        """Get open files from VSCode window titles and state"""
        open_files = []
        try:
            app_data = os.environ.get('APPDATA')
            if app_data:
                vscode_dir = 'Code'
                if 'cursor' in process_name.lower():
                    vscode_dir = 'Cursor'
                elif 'insiders' in process_name.lower():
                    vscode_dir = 'Code - Insiders'
                
                storage_file = os.path.join(app_data, vscode_dir, 'User', 'globalStorage', 'storage.json')
                if os.path.exists(storage_file):
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        storage_data = json.load(f)
                    
                    # Look for entries that contain file paths
                    for key, value in storage_data.items():
                        if isinstance(value, str) and 'file' in value and 'uri' in value:
                            try:
                                file_info = json.loads(value)
                                if isinstance(file_info, dict) and 'entries' in file_info:
                                    for entry in file_info['entries']:
                                        if 'resource' in entry and 'path' in entry['resource']:
                                            open_files.append(entry['resource']['path'])
                            except:
                                pass
        except Exception as e:
            self.logger.warning(f"Error getting VSCode open files from storage.json: {e}")

        # Fallback to window titles if storage.json parsing fails
        if not open_files:
            try:
                import win32gui
                import win32process
                
                def enum_window_callback(hwnd, results):
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process = psutil.Process(pid)
                            if process_name.lower() in process.name().lower():
                                title = win32gui.GetWindowText(hwnd)
                                if title and ' - ' in title:
                                    # VSCode title format: "filename - folder - VSCode"
                                    parts = title.split(' - ')
                                    if len(parts) >= 2:
                                        filename = parts[0].strip()
                                        if filename and not filename.startswith('●'):  # ● indicates unsaved
                                            open_files.append(filename)
                                        elif filename.startswith('●'):
                                            open_files.append(filename[1:].strip() + ' (unsaved)')
                        except:
                            pass
                    return True
                
                win32gui.EnumWindows(enum_window_callback, None)
            except Exception as e:
                self.logger.warning(f"Error getting VSCode open files from window titles: {e}")
            
        return list(set(open_files))[:10]  # Return unique files, max 10
    
    def _get_vscode_recent_projects(self) -> List[str]:
        """Get recent projects from VSCode"""
        recent_projects = []
        
        try:
            app_data = os.environ.get('APPDATA')
            if app_data:
                # Check various VSCode variants
                for vscode_dir in ['Code', 'Cursor', 'Code - Insiders']:
                    storage_file = os.path.join(app_data, vscode_dir, 'User', 'globalStorage', 'storage.json')
                    
                    if os.path.exists(storage_file):
                        with open(storage_file, 'r', encoding='utf-8') as f:
                            storage_data = json.load(f)
                            
                        # Look for recently opened workspaces
                        for key, value in storage_data.items():
                            if 'workspaces' in key.lower() and isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict) and 'path' in item:
                                        recent_projects.append(item['path'])
                                        
        except Exception as e:
            self.logger.warning(f"Error getting VSCode recent projects: {e}")
            
        return recent_projects[:10]  # Return top 10
    
    def _get_jetbrains_states(self) -> List[IDEState]:
        """Get JetBrains IDE states (PyCharm, IntelliJ, etc.)"""
        states = []
        
        jetbrains_ides = {
            'pycharm.exe': 'PyCharm',
            'pycharm64.exe': 'PyCharm',
            'idea.exe': 'IntelliJ IDEA',
            'idea64.exe': 'IntelliJ IDEA',
            'webstorm.exe': 'WebStorm',
            'webstorm64.exe': 'WebStorm',
            'clion.exe': 'CLion',
            'clion64.exe': 'CLion',
            'rider.exe': 'Rider',
            'rider64.exe': 'Rider',
            'goland.exe': 'GoLand',
            'goland64.exe': 'GoLand',
            'datagrip.exe': 'DataGrip',
            'datagrip64.exe': 'DataGrip'
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                process_name = proc.info['name'].lower()
                if process_name in jetbrains_ides:
                    ide_name = jetbrains_ides[process_name]
                    
                    # Try to get project path from window title or recent projects
                    project_path = None
                    recent_projects = self._get_jetbrains_recent_projects(ide_name)
                    
                    if recent_projects:
                        project_path = recent_projects[0]  # Assume first is current
                    
                    state = IDEState(
                        type=ide_name.lower().replace(' ', '_'),
                        process_name=proc.info['name'],
                        project_path=project_path,
                        open_files=self._get_jetbrains_open_files(proc.info['name'], proc.pid),
                        window_title=f"{ide_name}",
                        recent_projects=recent_projects
                    )
                    states.append(state)
                    
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
                
        return states
    
    def _get_jetbrains_recent_projects(self, ide_name: str) -> List[str]:
        """Get recent projects for JetBrains IDEs"""
        recent_projects = []
        
        try:
            # JetBrains IDEs store config in user home
            user_home = os.path.expanduser('~')
            
            # Map IDE names to config folders
            config_names = {
                'PyCharm': 'PyCharm',
                'IntelliJ IDEA': 'IntelliJIdea',
                'WebStorm': 'WebStorm',
                'CLion': 'CLion',
                'Rider': 'Rider',
                'GoLand': 'GoLand',
                'DataGrip': 'DataGrip'
            }
            
            config_name = config_names.get(ide_name, ide_name)
            
            # Look for config directories (they include version numbers)
            jetbrains_config_pattern = os.path.join(user_home, f'.{config_name}*', 'config')
            config_dirs = glob.glob(jetbrains_config_pattern)
            
            if not config_dirs:
                # Try Windows location
                app_data = os.environ.get('APPDATA')
                if app_data:
                    jetbrains_config_pattern = os.path.join(app_data, 'JetBrains', f'{config_name}*', 'options')
                    config_dirs = glob.glob(jetbrains_config_pattern)
            
            for config_dir in config_dirs:
                recent_projects_file = os.path.join(config_dir, 'recentProjects.xml')
                if os.path.exists(recent_projects_file):
                    # Parse XML to get recent projects
                    # Simple extraction without full XML parsing
                    with open(recent_projects_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Extract paths from the XML
                    import re
                    paths = re.findall(r'<entry key="([^"]+)"', content)
                    for path in paths:
                        # Convert $USER_HOME$ to actual path
                        if '$USER_HOME$' in path:
                            path = path.replace('$USER_HOME$', user_home)
                        path = path.replace('/', '\\')
                        if os.path.exists(path):
                            recent_projects.append(path)
                            
        except Exception as e:
            self.logger.warning(f"Error getting {ide_name} recent projects: {e}")
            
        return recent_projects[:10]
    
    def _get_sublime_states(self) -> List[IDEState]:
        """Get Sublime Text state"""
        states = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'sublime_text.exe' in proc.info['name'].lower():
                    # Get session data
                    session_file = self._find_sublime_session()
                    open_files = []
                    project_path = None
                    
                    if session_file and os.path.exists(session_file):
                        try:
                            with open(session_file, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                                
                            # Extract open files
                            for window in session_data.get('windows', []):
                                for view in window.get('views', []):
                                    file_path = view.get('file')
                                    if file_path:
                                        open_files.append(file_path)
                                        
                            # Get project folder
                            if session_data.get('folder_history'):
                                project_path = session_data['folder_history'][0]
                                
                        except Exception as e:
                            self.logger.warning(f"Error reading Sublime session: {e}")
                    
                    state = IDEState(
                        type='sublime_text',
                        process_name=proc.info['name'],
                        project_path=project_path,
                        open_files=open_files,
                        window_title="Sublime Text",
                        recent_projects=[]
                    )
                    states.append(state)
                    
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
                
        return states
    
    def _find_sublime_session(self) -> Optional[str]:
        """Find Sublime Text session file"""
        app_data = os.environ.get('APPDATA')
        if app_data:
            sublime_data = os.path.join(app_data, 'Sublime Text 3', 'Local')
            if os.path.exists(sublime_data):
                session_file = os.path.join(sublime_data, 'Session.sublime_session')
                if os.path.exists(session_file):
                    return session_file
                    
            # Try Sublime Text 4
            sublime_data = os.path.join(app_data, 'Sublime Text', 'Local')
            if os.path.exists(sublime_data):
                session_file = os.path.join(sublime_data, 'Session.sublime_session')
                if os.path.exists(session_file):
                    return session_file
                    
        return None
    
    def _get_notepad_plus_states(self) -> List[IDEState]:
        """Get Notepad++ state"""
        states = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'notepad++.exe' in proc.info['name'].lower():
                    # Get session data
                    session_file = self._find_notepad_plus_session()
                    open_files = []
                    
                    if session_file and os.path.exists(session_file):
                        # Parse XML session file
                        try:
                            import xml.etree.ElementTree as ET
                            tree = ET.parse(session_file)
                            root = tree.getroot()
                            
                            for file_elem in root.findall('.//File'):
                                filename = file_elem.get('filename')
                                if filename:
                                    open_files.append(filename)
                                    
                        except Exception as e:
                            self.logger.warning(f"Error reading Notepad++ session: {e}")
                    
                    state = IDEState(
                        type='notepad_plus',
                        process_name=proc.info['name'],
                        project_path=None,  # Notepad++ doesn't have projects
                        open_files=open_files,
                        window_title="Notepad++",
                        recent_projects=[]
                    )
                    states.append(state)
                    
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
                
        return states
    
    def _find_notepad_plus_session(self) -> Optional[str]:
        """Find Notepad++ session file"""
        app_data = os.environ.get('APPDATA')
        if app_data:
            npp_data = os.path.join(app_data, 'Notepad++')
            if os.path.exists(npp_data):
                session_file = os.path.join(npp_data, 'session.xml')
                if os.path.exists(session_file):
                    return session_file
                    
        return None
    
    def restore_ide_state(self, ide_state: IDEState) -> bool:
        """Restore an IDE with its state"""
        try:
            if ide_state.type == 'vscode':
                return self._restore_vscode(ide_state)
            elif ide_state.type.startswith('pycharm') or 'jetbrains' in ide_state.type:
                return self._restore_jetbrains(ide_state)
            elif ide_state.type == 'sublime_text':
                return self._restore_sublime(ide_state)
            elif ide_state.type == 'notepad_plus':
                return self._restore_notepad_plus(ide_state)
                
        except Exception as e:
            self.logger.error(f"Error restoring {ide_state.type}: {e}")
            
        return False
    
    def _restore_vscode(self, ide_state: IDEState) -> bool:
        """Restore VSCode with workspace and files"""
        cmd_parts = ['code']
        
        if ide_state.project_path:
            cmd_parts.append(f'"{ide_state.project_path}"')
            
        # Add files to open
        for file_path in ide_state.open_files:
            if os.path.exists(file_path):
                cmd_parts.append(f'"{file_path}"')
                
        os.system(' '.join(cmd_parts))
        return True
    
    def _restore_jetbrains(self, ide_state: IDEState) -> bool:
        """Restore JetBrains IDE with project"""
        # JetBrains IDEs can be opened with project path
        ide_executables = {
            'pycharm': 'pycharm',
            'intellij_idea': 'idea',
            'webstorm': 'webstorm',
            'clion': 'clion',
            'rider': 'rider',
            'goland': 'goland',
            'datagrip': 'datagrip'
        }
        
        exe_name = ide_executables.get(ide_state.type, ide_state.type)
        
        if ide_state.project_path and os.path.exists(ide_state.project_path):
            os.system(f'{exe_name} "{ide_state.project_path}"')
            return True
            
        return False
    
    def _restore_sublime(self, ide_state: IDEState) -> bool:
        """Restore Sublime Text with files"""
        cmd_parts = ['subl']
        
        if ide_state.project_path:
            cmd_parts.append(f'"{ide_state.project_path}"')
            
        for file_path in ide_state.open_files:
            if os.path.exists(file_path):
                cmd_parts.append(f'"{file_path}"')
                
        os.system(' '.join(cmd_parts))
        return True
    
    def _restore_notepad_plus(self, ide_state: IDEState) -> bool:
        """Restore Notepad++ with files"""
        cmd_parts = ['notepad++']
        
        for file_path in ide_state.open_files:
            if os.path.exists(file_path):
                cmd_parts.append(f'"{file_path}"')
                
        os.system(' '.join(cmd_parts))
        return True
    
    def _get_jetbrains_open_files(self, process_name: str, pid: int) -> List[str]:
        """Get open files from JetBrains IDE window titles"""
        open_files = []
        
        try:
            import win32gui
            import win32process
            
            def enum_window_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            # JetBrains title format: "filename [project] - IDE Name"
                            # or "filename - project - IDE Name"
                            if ' - ' in title:
                                parts = title.split(' - ')
                                if parts[0].strip():
                                    filename = parts[0].strip()
                                    # Remove project name in brackets if present
                                    if '[' in filename and ']' in filename:
                                        filename = filename[:filename.index('[')].strip()
                                    open_files.append(filename)
                return True
            
            win32gui.EnumWindows(enum_window_callback, None)
            
        except Exception as e:
            self.logger.warning(f"Error getting JetBrains open files: {e}")
            
        return list(set(open_files))[:10]
    
    def _get_process_main_window(self, pid: int) -> Optional[int]:
        """Get main window handle for a process"""
        try:
            import win32gui
            import win32process
            
            main_window = None
            
            def enum_window_callback(hwnd, param):
                nonlocal main_window
                if win32gui.IsWindowVisible(hwnd):
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        # Get the main window (not child windows)
                        if not win32gui.GetParent(hwnd):
                            main_window = hwnd
                            return False  # Stop enumeration
                return True
            
            win32gui.EnumWindows(enum_window_callback, None)
            return main_window
            
        except Exception as e:
            self.logger.warning(f"Error getting process window: {e}")
            return None