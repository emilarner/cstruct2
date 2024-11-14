import socket

host_endianness = "little"


def relative_endianness_resolver(endianness: str) -> str:
    """Resolve endian values, especially relative ones. This function is platform specific."""

    if endianness not in ["little", "big", "host", "network"]:
        raise AttributeError("Endianness can only be little, big, host, or network.")

    # Resolve relative endianness settings
    if endianness == "host":
        endianness = host_endianness

    elif endianness == "network":
        endianness = "big"

    return endianness


class SocketWrapper:
    """This exposes the write and read methods for a socket. This must be used for utilization of sockets for cstruct2."""

    def __init__(self, sock: socket.socket, rw_all=True):
        self.sock = sock
        self.rw_all = rw_all

    def write(self, data: bytes):
        self.sock.send(data, socket.MSG_WAITALL if self.rw_all else 0)

    def read(self, length: int) -> bytes:
        return self.sock.recv(length, socket.MSG_WAITALL if self.rw_all else 0)
