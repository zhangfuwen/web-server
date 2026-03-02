import asyncio
import websockets
import json
from threading import Thread

class WebSocketServer:
    def __init__(self, host='127.0.0.1', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.server = None
    
    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Handle incoming messages if needed
                pass
        finally:
            self.clients.discard(websocket)
    
    def broadcast(self, message):
        """Broadcast message to all clients (call from main thread)"""
        if self.clients:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(message),
                self.loop
            )
    
    async def _broadcast_async(self, message):
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.server = websockets.serve(self.handler, self.host, self.port)
        self.loop.run_until_complete(self.server)
        self.loop.run_forever()
    
    def start_thread(self):
        thread = Thread(target=self.start, daemon=True)
        thread.start()
        return thread

# Global instance
ws_server = WebSocketServer()
