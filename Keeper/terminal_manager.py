import logging
import os
import psutil
import json
from typing import Dict, List, Optional
import ctypes
import ctypes.wintypes
from pathlib import Path


class TerminalManager:
    """Manages terminal state extraction for various terminal applications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user32 = ctypes.windll.user32
        
    def get_terminal_info(self, process_name: str, hwnd: int) -> Dict:
        """Extract terminal information based on process type"""
        terminal_info = {
            'type': 'unknown',
            'process_name': process_name,
            'tabs': []
        }
        
        if 'WindowsTerminal' in process_name:
            terminal_info['type'] = 'windows_terminal'
            terminal_info['tabs'] = self._extract_windows_terminal_tabs(hwnd)
        elif 'Termius' in process_name:
            terminal_info['type'] = 'termius'
            terminal_info['tabs'] = self._extract_termius_tabs(hwnd)
        elif 'cmd.exe' in process_name:
            terminal_info['type'] = 'cmd'
            terminal_info['tabs'] = [self._extract_cmd_info(hwnd)]
        elif 'powershell' in process_name.lower():
            terminal_info['type'] = 'powershell'
            terminal_info['tabs'] = [self._extract_powershell_info(hwnd)]
        elif 'ConEmu' in process_name:
            terminal_info['type'] = 'conemu'
            terminal_info['tabs'] = self._extract_conemu_tabs(hwnd)
            
        return terminal_info
    
    def _extract_windows_terminal_tabs(self, hwnd: int) -> List[Dict]:
        """Extract Windows Terminal tabs information"""
        tabs = []
        
        try:
            # Try to get info from Windows Terminal settings
            local_app_data = os.environ.get('LOCALAPPDATA')
            if local_app_data:
                settings_path = os.path.join(
                    local_app_data, 
                    'Packages',
                    'Microsoft.WindowsTerminal_8wekyb3d8bbwe',
                    'LocalState',
                    'settings.json'
                )
                
                if os.path.exists(settings_path):
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        # Extract profile information
                        profiles = settings.get('profiles', {}).get('list', [])
                        
            # Get process information for each tab
            # This is limited without UI automation
            process_id = self._get_window_process_id(hwnd)
            if process_id:
                # Try to find child processes
                parent_process = psutil.Process(process_id)
                for child in parent_process.children(recursive=True):
                    if child.name() in ['cmd.exe', 'powershell.exe', 'pwsh.exe', 'bash.exe', 'wsl.exe']:
                        try:
                            # Get working directory
                            cwd = child.cwd()
                            
                            # Try to get environment variables for this process
                            env_vars = {}
                            try:
                                env_vars = self._get_process_environment(child.pid)
                            except:
                                pass
                            
                            tabs.append({
                                'profile': child.name(),
                                'workingDirectory': cwd,
                                'title': f"{child.name()} - {os.path.basename(cwd)}",
                                'pid': child.pid,
                                'environmentVariables': env_vars
                            })
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass
                            
        except Exception as e:
            self.logger.warning(f"Error extracting Windows Terminal tabs: {e}")
            
        # If no tabs found, at least return one with basic info
        if not tabs:
            tabs.append({
                'profile': 'Default',
                'workingDirectory': os.getcwd(),
                'title': 'Windows Terminal'
            })
            
        return tabs
    
    def _extract_cmd_info(self, hwnd: int) -> Dict:
        """Extract CMD.exe information"""
        tab_info = {
            'profile': 'CMD',
            'workingDirectory': os.getcwd(),
            'title': self._get_window_title(hwnd)
        }
        
        try:
            process_id = self._get_window_process_id(hwnd)
            if process_id:
                process = psutil.Process(process_id)
                tab_info['workingDirectory'] = process.cwd()
                tab_info['pid'] = process_id
                
                # Try to get current directory from window title
                title = tab_info['title']
                if ' - ' in title and ':' in title:
                    # Extract path from title like "C:\Users\Name - cmd.exe"
                    path_part = title.split(' - ')[0]
                    if os.path.exists(path_part):
                        tab_info['workingDirectory'] = path_part
                        
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
            
        return tab_info
    
    def _extract_powershell_info(self, hwnd: int) -> Dict:
        """Extract PowerShell information"""
        tab_info = {
            'profile': 'PowerShell',
            'workingDirectory': os.getcwd(),
            'title': self._get_window_title(hwnd)
        }
        
        try:
            process_id = self._get_window_process_id(hwnd)
            if process_id:
                process = psutil.Process(process_id)
                tab_info['workingDirectory'] = process.cwd()
                tab_info['pid'] = process_id
                
                # Determine PowerShell version
                if 'pwsh' in process.name().lower():
                    tab_info['profile'] = 'PowerShell Core'
                else:
                    tab_info['profile'] = 'Windows PowerShell'
                    
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
            
        return tab_info
    
    def _extract_termius_tabs(self, hwnd: int) -> List[Dict]:
        """Extract Termius tabs information"""
        # Termius stores connection info in its database
        tabs = []
        
        try:
            # Look for Termius data directory
            app_data = os.environ.get('APPDATA')
            if app_data:
                termius_data = os.path.join(app_data, 'Termius')
                if os.path.exists(termius_data):
                    # Basic info only - full extraction would require database access
                    tabs.append({
                        'profile': 'Termius',
                        'workingDirectory': 'Remote',
                        'title': self._get_window_title(hwnd)
                    })
                    
        except Exception as e:
            self.logger.warning(f"Error extracting Termius tabs: {e}")
            
        if not tabs:
            tabs.append({
                'profile': 'Termius',
                'workingDirectory': 'Remote',
                'title': 'Termius SSH'
            })
            
        return tabs
    
    def _extract_conemu_tabs(self, hwnd: int) -> List[Dict]:
        """Extract ConEmu tabs information"""
        tabs = []
        
        try:
            # ConEmu stores settings in xml
            app_data = os.environ.get('APPDATA')
            if app_data:
                conemu_xml = os.path.join(app_data, 'ConEmu.xml')
                if os.path.exists(conemu_xml):
                    # Basic parsing - full implementation would parse XML
                    pass
                    
            # Get basic info
            tabs.append({
                'profile': 'ConEmu',
                'workingDirectory': os.getcwd(),
                'title': self._get_window_title(hwnd)
            })
            
        except Exception as e:
            self.logger.warning(f"Error extracting ConEmu tabs: {e}")
            
        return tabs
    
    def _get_window_title(self, hwnd: int) -> str:
        """Get window title"""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    
    def _get_window_process_id(self, hwnd: int) -> Optional[int]:
        """Get process ID for a window"""
        process_id = ctypes.wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        return process_id.value if process_id.value else None
    
    def _get_process_environment(self, pid: int) -> Dict[str, str]:
        """Get environment variables for a process"""
        env_vars = {}
        
        try:
            process = psutil.Process(pid)
            # Try to get environment variables
            try:
                env_vars = process.environ()
            except psutil.AccessDenied:
                # Fallback: try to get from parent process or use current environment
                try:
                    parent = process.parent()
                    if parent:
                        env_vars = parent.environ()
                except:
                    # Use a subset of current environment as fallback
                    important_vars = ['PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 
                                    'NODE_PATH', 'JAVA_HOME', 'GOPATH', 'CARGO_HOME']
                    for var in important_vars:
                        if var in os.environ:
                            env_vars[var] = os.environ[var]
        except Exception as e:
            self.logger.debug(f"Could not get environment for PID {pid}: {e}")
            
        return env_vars
    
    def get_terminal_environment(self, process_id: int) -> Dict[str, str]:
        """Try to get environment variables from a terminal process"""
        env_vars = {}
        
        try:
            process = psutil.Process(process_id)
            # This is limited on Windows without additional privileges
            env_vars = process.environ()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            self.logger.warning(f"Cannot access environment for process {process_id}")
            
        return env_vars
    
    def save_terminal_state(self, terminal_info: Dict, context_path: Path) -> None:
        """Save terminal state to file"""
        terminal_file = context_path / "terminals.json"
        
        # Load existing data if file exists
        existing_data = []
        if terminal_file.exists():
            try:
                with open(terminal_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass
                
        # Append new terminal info
        existing_data.append(terminal_info)
        
        # Save back
        with open(terminal_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2)
    
    def restore_terminal_tabs(self, terminal_data: List[Dict]) -> None:
        """Attempt to restore terminal tabs"""
        for terminal in terminal_data:
            terminal_type = terminal.get('type')
            
            if terminal_type == 'windows_terminal':
                self._restore_windows_terminal(terminal)
            elif terminal_type == 'cmd':
                self._restore_cmd(terminal)
            elif terminal_type == 'powershell':
                self._restore_powershell(terminal)
            # Other terminal types would need specific handling
    
    def _restore_windows_terminal(self, terminal_data: Dict) -> None:
        """Restore Windows Terminal with tabs"""
        try:
            # Build command to open Windows Terminal with multiple tabs
            cmd_parts = ['wt']
            
            for i, tab in enumerate(terminal_data.get('tabs', [])):
                if i > 0:
                    cmd_parts.append(';')
                    cmd_parts.append('new-tab')
                    
                # Set working directory
                wd = tab.get('workingDirectory')
                if wd and os.path.exists(wd):
                    cmd_parts.extend(['-d', f'"{wd}"'])
                    
                # Set profile if specified
                profile = tab.get('profile')
                if profile:
                    if 'powershell' in profile.lower():
                        cmd_parts.extend(['powershell.exe'])
                    elif 'cmd' in profile.lower():
                        cmd_parts.extend(['cmd.exe'])
                
                # Handle environment variables
                env_vars = tab.get('environmentVariables', {})
                if env_vars:
                    # Create a batch file to set environment and launch terminal
                    self._create_env_batch_for_tab(tab, i)
                        
            # Execute command
            os.system(' '.join(cmd_parts))
            
        except Exception as e:
            self.logger.error(f"Error restoring Windows Terminal: {e}")
    
    def _restore_cmd(self, terminal_data: Dict) -> None:
        """Restore CMD window"""
        for tab in terminal_data.get('tabs', []):
            wd = tab.get('workingDirectory', os.getcwd())
            if os.path.exists(wd):
                os.system(f'start cmd /K "cd /d {wd}"')
    
    def _restore_powershell(self, terminal_data: Dict) -> None:
        """Restore PowerShell window"""
        for tab in terminal_data.get('tabs', []):
            wd = tab.get('workingDirectory', os.getcwd())
            if os.path.exists(wd):
                os.system(f'start powershell -NoExit -Command "Set-Location -Path \'{wd}\'"')
    
    def _create_env_batch_for_tab(self, tab: Dict, tab_index: int) -> str:
        """Create a batch file to set environment variables for a tab"""
        try:
            import tempfile
            from datetime import datetime
            
            # Create temp batch file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_file = os.path.join(tempfile.gettempdir(), f'terminal_env_{timestamp}_{tab_index}.bat')
            
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write(f'REM Terminal environment restoration\n')
                f.write(f'REM Tab: {tab.get("title", "Unknown")}\n\n')
                
                # Set environment variables
                env_vars = tab.get('environmentVariables', {})
                for key, value in env_vars.items():
                    # Escape special characters
                    value = value.replace('%', '%%').replace('"', '""')
                    f.write(f'set "{key}={value}"\n')
                
                # Change to working directory
                wd = tab.get('workingDirectory')
                if wd and os.path.exists(wd):
                    f.write(f'\ncd /d "{wd}"\n')
                
                # Keep window open
                f.write('\ncmd /k\n')
            
            return batch_file
            
        except Exception as e:
            self.logger.error(f"Error creating env batch: {e}")
            return None