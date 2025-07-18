"""Quick response mechanism for Context Keeper plugin"""

import json
import threading
import time
from typing import Dict, Callable


class QuickResponseHandler:
    """Handles immediate responses while processing continues in background"""
    
    def __init__(self, write_response: Callable):
        self.write_response = write_response
        
    def handle_with_progress(self, func: Callable, params: dict, 
                           initial_message: str = "Processing...") -> dict:
        """Send immediate response and process in background"""
        
        # Send immediate 
        self.write_response({
            "success": True,
            "message": initial_message,
            "status": "processing"
        })
        
        # Process in background
        result = {"success": False, "message": "Processing failed"}
        
        def background_task():
            nonlocal result
            try:
                result = func(params)
            except Exception as e:
                result = {"success": False, "message": str(e)}
        
        # Start background thread
        thread = threading.Thread(target=background_task)
        thread.daemon = True
        thread.start()
        
        # Wait briefly for completion (max 2 seconds)
        thread.join(timeout=2.0)
        
        if thread.is_alive():
            # Still processing, return progress message
            return {
                "success": True,
                "message": f"{initial_message} (background processing)",
                "status": "background"
            }
        else:
            # Completed, return actual result
            return result