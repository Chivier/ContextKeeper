import json
import logging
import os
import glob
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class EnvironmentManager:
    """Manages environment variable snapshots with timestamped files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def keep_environment(self, context_name: str) -> str:
        """Keep ALL current environment variables to timestamped file"""
        # Get all environment variables
        env_vars = dict(os.environ)
        
        # Create timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save to file with specific naming pattern
        env_file = f".g_assist_env_{timestamp}.json"
        env_path = Path("contexts") / context_name / env_file
        
        # Ensure directory exists
        env_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save all environment variables
        with open(env_path, 'w', encoding='utf-8') as f:
            json.dump(env_vars, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Kept {len(env_vars)} environment variables to {env_path}")
        return str(env_path)
    
    def restore_environment(self, context_name: str) -> str:
        """Restore environment variables from the latest file"""
        # Find all environment files for this context
        pattern = str(Path("contexts") / context_name / ".g_assist_env_*.json")
        env_files = glob.glob(pattern)
        
        if not env_files:
            raise FileNotFoundError(f"No environment files found for context: {context_name}")
        
        # Sort by datetime to get the latest
        env_files.sort(key=lambda x: self._extract_datetime(x), reverse=True)
        latest_env_file = env_files[0]
        
        # Load environment variables
        with open(latest_env_file, 'r', encoding='utf-8') as f:
            env_vars = json.load(f)
        
        # Clear current environment and set new variables
        os.environ.clear()
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Log restoration
        self._log_restoration(latest_env_file, len(env_vars))
        
        # Optionally create batch file for system-wide restore
        self.create_env_batch(env_vars, context_name)
        
        return str(latest_env_file)
    
    def _extract_datetime(self, filename: str) -> datetime:
        """Extract datetime from filename .g_assist_env_YYYYMMDD_HHMMSS.json"""
        pattern = r'\.g_assist_env_(\d{8}_\d{6})\.json'
        match = re.search(pattern, filename)
        
        if match:
            datetime_str = match.group(1)
            return datetime.strptime(datetime_str, '%Y%m%d_%H%M%S')
        return datetime.min
    
    def create_env_batch(self, env_vars: Dict[str, str], context_name: str) -> None:
        """Create batch file for manual environment restoration"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_file = os.path.join("contexts", context_name, f"restore_env_{timestamp}.bat")
        
        os.makedirs(os.path.dirname(batch_file), exist_ok=True)
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write(f'REM Environment restoration for {context_name}\n')
            f.write(f'REM Generated at {timestamp}\n\n')
            
            for key, value in env_vars.items():
                # Escape special characters for batch file
                value = value.replace('%', '%%')
                value = value.replace('"', '""')
                f.write(f'set "{key}={value}"\n')
            
            f.write('\necho Environment variables restored successfully.\n')
            f.write('pause\n')
    
    def list_environment_snapshots(self, context_name: str) -> List[Dict]:
        """List all environment snapshots for a context"""
        pattern = os.path.join("contexts", context_name, ".g_assist_env_*.json")
        env_files = glob.glob(pattern)
        
        snapshots = []
        for file in env_files:
            dt = self._extract_datetime(file)
            size = os.path.getsize(file)
            snapshots.append({
                'file': file,
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'size': size,
                'age_hours': (datetime.now() - dt).total_seconds() / 3600
            })
        
        # Sort by datetime, newest first
        snapshots.sort(key=lambda x: x['datetime'], reverse=True)
        return snapshots
    
    def cleanup_old_snapshots(self, context_name: str, keep_last: int = 5) -> None:
        """Clean up old environment snapshots, keeping only the most recent ones"""
        snapshots = self.list_environment_snapshots(context_name)
        
        if len(snapshots) > keep_last:
            for snapshot in snapshots[keep_last:]:
                os.remove(snapshot['file'])
                self._log_cleanup(snapshot['file'])
    
    def _log_restoration(self, file_path: str, var_count: int) -> None:
        """Log environment restoration"""
        self.logger.info(f"Restored {var_count} environment variables from {file_path}")
    
    def _log_cleanup(self, file_path: str) -> None:
        """Log file cleanup"""
        self.logger.info(f"Cleaned up old environment snapshot: {file_path}")