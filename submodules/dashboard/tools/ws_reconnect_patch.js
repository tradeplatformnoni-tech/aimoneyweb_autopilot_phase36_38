// tools/ws_reconnect_patch.js
console.log("📡 WebSocket reconnect patch activated");

function autoReconnectWS(url, onMessage) {
    let socket;
    function connect() {
        socket = new WebSocket(url);
        socket.onopen = () => console.log("✅ WebSocket connected:", url);
        socket.onmessage = onMessage;
        socket.onclose = () => {
            console.warn("⚠️ WebSocket closed. Reconnecting in 5s...");
            setTimeout(connect, 5000);
        };
        socket.onerror = (err) => console.error("WebSocket error:", err);
    }
    connect();
}

window.autoReconnectWS = autoReconnectWS;
