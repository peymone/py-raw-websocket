import socket
from threading import Thread

from websock import RawWebsocketServer
from config import ServerConfig, WebsockConfig


class TCPServer:
    pass


def serve_tcp(host: str, port: int, max_connections: int) -> None:
    """Start a TCP server that listens for incoming connections and initiating upgrade to WebSocket protocol"""

    # Create and setup TCP socket

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.settimeout(ServerConfig.check_exit_signals_period)
    server_sock.bind((host, port))
    server_sock.listen(max_connections)
    print(f"TCP server started on {host}:{port}. Enter Ctrl+C to exit.")

    while not WebsockConfig.exit_signal:  # Accept incoming TCP connections
        try:
            client_sock, addr = server_sock.accept()
            print(f"Connection established with {addr[0]}:{addr[1]}")
            client_sock.settimeout(WebsockConfig.check_exit_signals_period)

            # Start websocket communication in explicit thread for client
            t = Thread(target=websock_server.start_communication, args=(client_sock,))
            t.start()

        except socket.timeout:  # stop accepting every n second
            continue

        except Exception as e:
            print("Error occurred while serving TCP: ", e)
            break

    print("Shutting down TCP server...")
    server_sock.close()


if __name__ == "__main__":
    try:
        websock_server = RawWebsocketServer()
        serve_tcp(ServerConfig.host, ServerConfig.port, ServerConfig.max_connections)

    except KeyboardInterrupt:
        WebsockConfig.exit_signal = True
