"""
Simple WebSocket server for Molt Server.
Uses synchronous websockets-sync library for thread-safe operation.
"""

try:
    from websockets.sync.server import serve, ServerConnection
except ImportError:
    # Fallback for older websockets versions
    from websockets.server import serve, ServerConnection

import threading
import json
import time

class WebSocketServer:
    def __init__(self, host='127.0.0.1', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.lock = threading.Lock()
        self.server = None
        self._stop = threading.Event()
    
    def handler(self, websocket):
        """Handle a single WebSocket connection."""
        with self.lock:
            self.clients.add(websocket)
        try:
            for message in websocket:
                # Echo or process messages if needed
                pass
        finally:
            with self.lock:
                self.clients.discard(websocket)
    
    def broadcast(self, message):
        """Broadcast message to all connected clients."""
        with self.lock:
            clients = list(self.clients)
        
        for client in clients:
            try:
                client.send(message)
            except Exception:
                # Client disconnected, will be cleaned up
                pass
    
    def start(self):
        """Start the WebSocket server (blocking)."""
        with serve(self.handler, self.host, self.port) as self.server:
            self.server.serve_forever()
    
    def start_thread(self):
        """Start the WebSocket server in a background thread."""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        time.sleep(0.5)  # Give server time to start
        return thread
    
    def stop(self):
        """Stop the WebSocket server."""
        self._stop.set()
        if self.server:
            self.server.shutdown()

# Global instance
ws_server = WebSocketServer()
