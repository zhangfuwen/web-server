class WebSocketClient {
    constructor(url = 'ws://localhost:8765') {
        this.url = url;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        this.ws.onopen = () => console.log('WS connected');
        this.ws.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
        this.ws.onclose = () => setTimeout(() => this.connect(), this.reconnectInterval);
    }
    
    handleMessage(msg) {
        console.log('WS message:', msg);
        // Handle task:updated, task:created, etc.
    }
}

export default new WebSocketClient();
