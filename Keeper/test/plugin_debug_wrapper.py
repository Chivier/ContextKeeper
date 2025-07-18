#!/usr/bin/env python3
"""
Debug wrapper for G-Assist plugin to capture all stdin/stdout communication
This helps diagnose communication issues with G-Assist
"""

import sys
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Import the actual plugin from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from plugin import main as plugin_main

# Setup debug logging
DEBUG_DIR = Path.home() / ".keeper" / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Create session-specific log file
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
session_log = DEBUG_DIR / f"session_{session_id}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(session_log),
        logging.StreamHandler(sys.stderr)  # Also log to stderr for immediate visibility
    ]
)

logger = logging.getLogger(__name__)

class DebugPipe:
    """Wrapper for stdin/stdout to log all communication"""
    
    def __init__(self, pipe, name):
        self.pipe = pipe
        self.name = name
        self.buffer = ""
        
    def read(self, size=-1):
        """Read from pipe and log"""
        try:
            data = self.pipe.read(size)
            logger.debug(f"{self.name}.read({size}) -> {len(data) if data else 0} bytes")
            if data:
                logger.debug(f"{self.name} data: {repr(data[:200])}...")
                self.buffer += data
                # Try to parse as JSON if we have a complete message
                if '\n' in data or size == -1:
                    try:
                        json_obj = json.loads(self.buffer.strip())
                        logger.info(f"{self.name} JSON: {json.dumps(json_obj, indent=2)}")
                        self.buffer = ""
                    except:
                        pass
            return data
        except Exception as e:
            logger.error(f"{self.name}.read error: {e}")
            raise
            
    def write(self, data):
        """Write to pipe and log"""
        try:
            logger.debug(f"{self.name}.write({len(data)} bytes)")
            logger.debug(f"{self.name} data: {repr(data[:200])}...")
            # Try to parse as JSON
            try:
                json_obj = json.loads(data.strip())
                logger.info(f"{self.name} JSON: {json.dumps(json_obj, indent=2)}")
            except:
                pass
            result = self.pipe.write(data)
            self.pipe.flush()
            return result
        except Exception as e:
            logger.error(f"{self.name}.write error: {e}")
            raise
            
    def flush(self):
        """Flush the pipe"""
        try:
            return self.pipe.flush()
        except:
            pass
            
    def __getattr__(self, name):
        """Delegate other methods to the wrapped pipe"""
        return getattr(self.pipe, name)

def debug_main():
    """Main entry point with debug wrapping"""
    logger.info("="*60)
    logger.info("G-Assist Keeper Plugin Debug Wrapper Starting")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Log file: {session_log}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working dir: {Path.cwd()}")
    logger.info("="*60)
    
    # Wrap stdin/stdout
    original_stdin = sys.stdin
    original_stdout = sys.stdout
    
    try:
        # For binary mode (Windows pipes)
        if hasattr(sys.stdin, 'buffer'):
            sys.stdin.buffer = DebugPipe(sys.stdin.buffer, "stdin")
        else:
            sys.stdin = DebugPipe(sys.stdin, "stdin")
            
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer = DebugPipe(sys.stdout.buffer, "stdout")
        else:
            sys.stdout = DebugPipe(sys.stdout, "stdout")
        
        logger.info("Starting plugin main loop...")
        
        # Run the actual plugin
        result = plugin_main()
        
        logger.info(f"Plugin exited with result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in debug wrapper: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        
        # Try to send error response
        try:
            error_response = {
                "success": False,
                "message": f"Plugin crashed: {str(e)}"
            }
            original_stdout.write(json.dumps(error_response) + "<<END>>")
            original_stdout.flush()
        except:
            pass
            
        return 1
        
    finally:
        # Restore original pipes
        sys.stdin = original_stdin
        sys.stdout = original_stdout
        logger.info("Debug wrapper shutting down")

if __name__ == "__main__":
    sys.exit(debug_main())