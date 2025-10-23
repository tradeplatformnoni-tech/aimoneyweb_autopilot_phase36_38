# NEOLIGHT_PHASE4700_PORT_HANDLER
import socket, os

def get_available_port(default=5050):
    # Respect env override if provided
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    # Try default first
    if _is_free(default):
        return default
    # Otherwise find a free ephemeral
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def _is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0
