# Raw WebSocket implementation on python

*It was written solely for the purpose of studying the operation of the protocol and do not use any external libraries. More of protocol on [wikipedia](https://en.wikipedia.org/wiki/WebSocket)*

**In a nutshell:**

*WebSocket is a protocol for full-duplex communication over a single TCP connection. After the HTTP handshake, it switches to frame-based data transfer (including control frames such as Ping/Pong/Close), with mandatory masking of client frames.*

1. *The client connects to the server over HTTP with a strictly defined request (an upgrade request — example below).*
2. *The server responds to the client with an upgrade response.*
3. *Now WebSocket communication begins (a TCP socket with a defined message structure; unlike raw sockets, it’s just better!).*

```text
Client                                             Server
  |                                                  |
  | 1. HTTP GET /chat HTTP/1.1                       |
  |    Upgrade: websocket                           |
  |    Connection: Upgrade                           |
  |    Sec-WebSocket-Key: ...                        |
  |    Sec-WebSocket-Version: 13                     |
  |------------------------------------------------->|
  |                                                  |
  | 2. HTTP/1.1 101 Switching Protocols              |
  |    Upgrade: websocket                           |
  |    Connection: Upgrade                           |
  |    Sec-WebSocket-Accept: ...                     |
  |<-------------------------------------------------|
  |                                                  |
  | 3. WebSocket communication begins                |
  |    (TCP socket + framed messages)                |
  |                                                  |
  |  Data frame (masked from client)                 |
  |------------------------------------------------->|
  |<-------------------------------------------------|
  |  Data frame (unmasked from server)               |
  |                                                  |
  |  Ping  ----------------------------------------> |
  |  <---------------------------------------- Pong  |
  |                                                  |
  |  Close ----------------------------------------> |
  |  <--------------------------------------- Close  |
  |                                                  |
  |  TCP connection closed                           |
  |                                                  |
```

## What this code does:

  - [x] *Initial Handsahake*
  - [x] *Reactions for all opcodes*
  - [x] *Frame header parsing/building*
  - [x] *Dispaying and echo complete messages*

## Installation

1. *Copy code in your machine*
2. *Start server with a command: `py ./src/server.py`*
