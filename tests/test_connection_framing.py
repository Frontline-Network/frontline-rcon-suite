"""Real framing code with deterministic sockets; never contacts a game server."""

import json
import socket
import struct
from unittest.mock import Mock

import pytest

from rcon import connection


class Socket:
    def __init__(self, chunks=()):
        self.chunks = list(chunks)
        self.timeout = 20
        self.reads = 0
        self.written = bytearray()
        self.close_count = 0
        self.on_read = lambda: None

    def settimeout(self, value):
        self.timeout = value

    def gettimeout(self):
        return self.timeout

    def recv(self, size):
        self.reads += 1
        self.on_read()
        if self.reads > 100:
            pytest.fail("Response loop did not stop")
        chunk = self.chunks.pop(0) if self.chunks else b""
        if isinstance(chunk, Exception):
            raise chunk
        if len(chunk) > size:
            self.chunks.insert(0, chunk[size:])
        return chunk[:size]

    def send(self, data):
        # Simulate partial TCP writes.
        written = min(4, len(data))
        self.written.extend(data[:written])
        return written

    def sendall(self, data):
        while data:
            data = data[self.send(data) :]

    def shutdown(self, _how):
        pass

    def close(self):
        self.close_count += 1


def make_connection(monkeypatch, chunks=()):
    sock = Socket(chunks)
    monkeypatch.setattr(connection.socket, "socket", lambda *_: sock)
    return connection.HLLConnection(), sock


def frame(request_id=1, key=None):
    body = json.dumps(
        {
            "name": "GetServerInformation",
            "version": 2,
            "statusCode": 200,
            "statusMessage": "OK",
            "contentBody": "Huế – Test",
        },
        ensure_ascii=False,
    ).encode()
    if key:
        body = bytes(byte ^ key[i % len(key)] for i, byte in enumerate(body))
    return (
        struct.pack(
            connection.HEADER_FORMAT,
            connection.MAGIC_HEADER_VALUE,
            request_id,
            len(body),
        )
        + body
    )


@pytest.mark.parametrize("key", [None, b"\x04\x07\x81\xf0"])
def test_fragmented_header_and_utf8_body_are_reassembled(monkeypatch, key):
    packet = frame(key=key)
    conn, sock = make_connection(
        monkeypatch, [packet[i : i + 2] for i in range(0, len(packet), 2)]
    )
    conn.xorkey = key
    response = conn.receive(1)
    assert response.content == "Huế – Test"
    assert sock.reads > 6
    assert sock.timeout == 20
    assert not conn.closed


def test_partial_writes_send_one_complete_packet(monkeypatch):
    conn, sock = make_connection(monkeypatch)
    handle = conn.send("GetServerInformation", 2, {})
    header, body = handle.request.to_bytes()
    assert sock.written == header + body


@pytest.mark.parametrize("chunks", [[], [b"abc"], [frame()[:12]], [frame()[:20]]])
def test_eof_at_any_point_closes_and_releases_lock(monkeypatch, chunks):
    conn, sock = make_connection(monkeypatch, chunks)
    with pytest.raises(connection.HLLBrokenConnectionError, match="closed during"):
        conn.receive(1)
    assert sock.reads <= 3
    assert conn.closed
    assert sock.close_count == 1
    assert not conn.mu.locked()
    conn.close()
    assert sock.close_count == 1


@pytest.mark.parametrize("size", [0, connection.MAX_RESPONSE_BYTES + 1, 2**32 - 1])
def test_invalid_length_is_rejected_before_reading_body(monkeypatch, size):
    conn, sock = make_connection(
        monkeypatch,
        [struct.pack(connection.HEADER_FORMAT, connection.MAGIC_HEADER_VALUE, 1, size)],
    )
    with pytest.raises(connection.HLLBrokenConnectionError, match="size"):
        conn.receive(1)
    assert sock.reads == 1 and conn.closed


def test_bad_magic_is_rejected(monkeypatch):
    conn, _ = make_connection(
        monkeypatch, [struct.pack(connection.HEADER_FORMAT, 0, 1, 3)]
    )
    with pytest.raises(connection.HLLBrokenConnectionError, match="header"):
        conn.receive(1)
    assert conn.closed


@pytest.mark.parametrize("body", [b"\xff", b"not json", b"{}", b"[]", b"null"])
def test_malformed_response_is_classified_without_exposing_body(monkeypatch, body):
    header = struct.pack(
        connection.HEADER_FORMAT, connection.MAGIC_HEADER_VALUE, 1, len(body)
    )
    conn, _ = make_connection(monkeypatch, [header, body])
    with pytest.raises(
        connection.HLLBrokenConnectionError, match="^Malformed RCON response$"
    ):
        conn.receive(1)
    assert conn.closed


def test_timeout_invalidates_connection(monkeypatch):
    conn, sock = make_connection(monkeypatch, [socket.timeout("test")])
    with pytest.raises(TimeoutError):
        conn.receive(1)
    assert conn.closed and sock.close_count == 1
    assert not conn.mu.locked()


def test_trickling_body_cannot_extend_total_body_deadline(monkeypatch):
    packet = frame()
    conn, sock = make_connection(
        monkeypatch, [packet[:12], *[bytes([b]) for b in packet[12:]]]
    )
    now = [0.0]
    monkeypatch.setattr(connection.time, "monotonic", lambda: now[0])
    sock.on_read = lambda: now.__setitem__(0, now[0] + 1)
    with pytest.raises(TimeoutError, match="deadline"):
        conn.receive(1)
    assert sock.reads == 4
    assert conn.closed


def test_out_of_order_responses_are_cached_without_extra_reads(monkeypatch):
    conn, sock = make_connection(monkeypatch, [frame(2), frame(1)])
    assert conn.receive(1).request_id == 1
    reads = sock.reads
    assert conn.receive(2).request_id == 2
    assert sock.reads == reads


def test_send_error_is_not_retried_by_connection(monkeypatch):
    conn, sock = make_connection(monkeypatch)
    sock.sendall = Mock(side_effect=BrokenPipeError("partial write"))
    with pytest.raises(BrokenPipeError):
        conn.send("KickPlayer", 2, "synthetic")
    assert sock.sendall.call_count == 1
    assert conn.closed


def test_failed_handshake_closes_unpooled_socket(monkeypatch):
    conn, sock = make_connection(monkeypatch)
    sock.connect = Mock()
    conn.exchange = Mock(
        side_effect=connection.HLLBrokenConnectionError("bad handshake")
    )
    with pytest.raises(connection.HLLBrokenConnectionError):
        conn.connect("127.0.0.1", 1, "not-a-password")
    assert sock.close_count == 1


def test_authentication_failure_remains_non_retryable(monkeypatch):
    conn, sock = make_connection(monkeypatch)
    sock.connect = Mock()
    hello = Mock(content="dGVzdA==")
    login = Mock()
    login.raise_for_status.side_effect = connection.HLLCommandError(401, "Unauthorized")
    conn.exchange = Mock(side_effect=[hello, login])
    with pytest.raises(connection.HLLCommandError) as failure:
        conn.connect("127.0.0.1", 1, "not-a-password")
    assert failure.value.status_code == 401
    assert conn.exchange.call_count == 2
    assert conn.closed and sock.close_count == 1
