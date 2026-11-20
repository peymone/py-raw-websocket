import struct
import base64
import hashlib
from socket import socket, timeout

from config import WebsockConfig as cfg


class RawWebsocketServer:
    """Raw implementation of WebSocket protocol"""

    def start_communication(self, sock: socket) -> None:
        """Perform the Websocket handshake and start receiving/send frames in endless loop"""

        handshake_performed = close_reason = msg_opcode = opcode = None
        client = ":".join([str(addr) for addr in sock.getpeername()])
        msg = b""

        while not cfg.exit_signal or opcode != cfg.OPCODE_CLOSE:
            try:
                if not handshake_performed:
                    self.perform_handshake(sock)
                    handshake_performed = True
                    print(f"WebSocket handshake performed for {client}")

                payload, opcode, fin = self.recv_frame(sock)

                if fin == cfg.FIN_LAST:  # Last frame of msg

                    if opcode == cfg.OPCODE_CONTINUE:  # Save frame to msg
                        msg += payload

                    if opcode == cfg.OPCODE_CLOSE:  # Stop communication
                        close_reason = payload.decode()

                    if opcode == cfg.OPCODE_PING:  # Send ping frame
                        self.send_message(sock, b"", cfg.OPCODE_PONG)
                        continue

                    if opcode == cfg.OPCODE_PONG:  # Ignore pong frame
                        continue

                    if opcode in cfg.TYPE_OPCODES:  # Save frame and type of msg
                        msg_opcode = opcode
                        msg += payload

                elif fin == cfg.FIN_CONTINUE:  # Not last frame of msg

                    if opcode == cfg.OPCODE_CONTINUE:  # Save frame to msg
                        msg += payload

                    if opcode in cfg.TYPE_OPCODES:  # Save frame and type of msg
                        msg_opcode = opcode
                        msg += payload

                    continue

                # Display received message and echo it back
                print(f"{client} sent message: {msg.decode()}")
                self.send_message(sock, msg, msg_opcode)
                msg = b""

            except timeout:
                continue

            except Exception as e:
                print(f"Error occured while handling the {client}: {e}")
                break

        if close_reason:
            print(f"{client} sent close opcode with reason: ", close_reason)

        self.stop_communication(sock)

    def stop_communication(self, sock: socket) -> None:
        """Send connection close frame to the client and close TCP socket"""

        self.send_message(sock, b"", cfg.OPCODE_CLOSE)
        sock.close()

    def perform_handshake(self, sock: socket) -> None:
        """Perform HTTP handshake for upgrading to WebSocket protocol according to the specification"""

        # Read HTTP upgrade request from the client

        request = b""
        while cfg.REQUEST_TERMINTOR not in request:
            request += sock.recv(1024)

        # Parse http headers and generate WebSocket accept Key

        headers = self._parse_websock_upgrade_headers(request)
        conn_accept_key = self._generate_websock_conn_accept_key(headers)

        # Build and send connection acceptance response

        conn_accept_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {conn_accept_key}\r\n"
            "Sec-WebSocket-Protocol: chat\r\n\r\n"
        )

        sock.sendall(conn_accept_response.encode())

    def send_message(self, sock: socket, message: bytes, opcode: int = 1) -> None:
        """Split message and send it to the client as WebSocket frames"""

        # Send control frame to the client

        if opcode in cfg.CONTROL_OPCODES:
            payload = message[: cfg.PAYLOAD_LEN_MAX_INLINE]
            header = self._build_frame_header(cfg.FIN_LAST, opcode, len(payload))
            sock.sendall(header + payload)

            return

        # Check if message is empty

        if not message:
            return

        # Send message frames to the client

        sent_bytes, first_frame, message_len = 0, True, len(message)

        while sent_bytes < message_len:

            # Chunk message on frames
            frame = message[sent_bytes : sent_bytes + cfg.max_payload_size]
            frame_len = len(frame)

            # Add frame length to sent bytes
            sent_bytes += frame_len
            last_frame = sent_bytes >= message_len

            # Build frame header
            header = self._build_frame_header(
                fin=cfg.FIN_LAST if last_frame else cfg.FIN_CONTINUE,
                opcode=opcode if first_frame else cfg.OPCODE_CONTINUE,
                payload_len=frame_len,
            )

            # Send frame to the client and umark first frame
            sock.sendall(header + frame)
            first_frame = False

    def recv_frame(self, sock: socket) -> tuple[bytes, int, int]:
        """Receive WebSocket frame from the client and return the payload, opcode and fin bits"""

        frame_header = self._recv_exact(sock, 2)

        if len(frame_header) < 2:
            raise ValueError("Incomplete frame header received")

        # Parse the first byte of the frame header

        fin = (frame_header[0] & 0x80) >> 7  # last frame indicator
        rsv1 = (frame_header[0] & 0x40) >> 6  # reserved bit for extensions
        rsv2 = (frame_header[0] & 0x20) >> 5  # reserved bit for extensions
        rsv3 = (frame_header[0] & 0x10) >> 4  # reserved bit for extensions
        opcode = frame_header[0] & 0x0F  # control bit indicating the type of frame

        # Parse the second byte of the frame header

        masked = (frame_header[1] & 0x80) >> 7  # masked or not
        payload_length = frame_header[1] & 0x7F

        # Receive the actual payload message

        if payload_length == 126:  # Payload length in 2 bytes
            payload_length = struct.unpack(">H", sock.recv(2))[0]

        elif payload_length == 127:  # Payload length in 8 bytes
            payload_length = struct.unpack(">Q", sock.recv(8))[0]

        # Receive the mask of the payload

        if masked:
            mask = self._recv_exact(sock, 4)

        # Receive the payload

        payload = self._recv_exact(sock, payload_length)

        # Unmask the payload

        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

        return payload, opcode, fin

    def _recv_exact(self, sock: socket, payload_len: int) -> bytearray:
        """Continue to receive bytes from TCP socket until it reaches the required payload size"""

        received_bytes = bytearray()

        while len(received_bytes) < payload_len:
            chunk = sock.recv(payload_len - len(received_bytes))
            if not chunk:
                raise ConnectionError(f"Connection with {sock.getpeername()} is closed")

            received_bytes.extend(chunk)

        return received_bytes

    def _build_frame_header(self, fin: int, opcode: int, payload_len: int) -> bytes:
        """Build WebSocket frame header"""

        first_byte = ((fin & 0x01) << 7) | (opcode & 0x0F)  # RSV is omitted

        if payload_len <= 125:
            second_byte = payload_len
            frame_header = struct.pack("!BB", first_byte, second_byte)

        elif payload_len <= 0xFFFF:
            second_byte = cfg.PAYLOAD_LEN_EXTENDED_16
            frame_header = struct.pack("!BBH", first_byte, second_byte, payload_len)

        else:
            second_byte = cfg.PAYLOAD_LEN_EXTENDED_64
            frame_header = struct.pack("!BBQ", first_byte, second_byte, payload_len)

        return frame_header

    def _parse_websock_upgrade_headers(self, request: bytes) -> dict[str, str]:
        """Parse and check required HTTP headers for WeSocket Upgrade request"""

        # Parse HTTP headers

        request = request.decode()
        headers: dict[str, str] = {}

        for line in request.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Check required HTTP headers

        if "Upgrade" not in headers or headers["Upgrade"] != "websocket":
            raise ValueError("Missing or invalid Upgrade header")

        if "Connection" not in headers or headers["Connection"] != "Upgrade":
            raise ValueError("Missing or invalid Connection header")

        if "Sec-WebSocket-Key" not in headers:
            raise ValueError("Missing Sec-WebSocket-Key header")

        if "Sec-WebSocket-Version" not in headers:
            raise ValueError("Missing Sec-WebSocket-Version header")

        if headers["Sec-WebSocket-Version"] != "13":
            raise ValueError("Invalid Sec-WebSocket-Version header")

        return headers

    def _generate_websock_conn_accept_key(self, headers: dict[str, str]) -> str:
        """Generate the Sec-WebSocket-Accept key based on the Sec-WebSocket-Key from the client + GUID"""

        client_key = headers["Sec-WebSocket-Key"]
        client_key_and_guid = (client_key + cfg.GUID).encode()

        # Concatenate the client key with the GUID and compute the SHA-1 hash
        sha1_hash = hashlib.sha1(client_key_and_guid).digest()

        # Encode the hash in base64 to get the accept key and decode it to a string
        accept_key = base64.b64encode(sha1_hash)

        return accept_key.decode()
