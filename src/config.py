from dataclasses import dataclass


@dataclass
class ServerConfig:
    port: int = 8765
    host: str = "localhost"
    max_connections: int = 5
    check_exit_signals_period: float = 0.5


class WebsockConfig:
    exit_signal: bool = False
    max_payload_size: int = 2**63 - 1
    check_exit_signals_period: float = 5.5

    # Unchangeable
    GUID: str = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    REQUEST_TERMINTOR: bytes = b"\r\n\r\n"
    FIN_LAST: int = 1
    FIN_CONTINUE: int = 0
    OPCODE_TEXT: int = 0x1
    OPCODE_BIN: int = 0x2
    OPCODE_CLOSE: int = 0x8
    OPCODE_PING: int = 0x9
    OPCODE_PONG: int = 0xA
    OPCODE_CONTINUE: int = 0x0
    PAYLOAD_LEN_MAX_INLINE: int = 125
    PAYLOAD_LEN_EXTENDED_16: int = 126
    PAYLOAD_LEN_EXTENDED_64: int = 127

    TYPE_OPCODES: tuple = OPCODE_TEXT, OPCODE_BIN
    CONTROL_OPCODES: tuple = OPCODE_PING, OPCODE_PONG, OPCODE_CLOSE
