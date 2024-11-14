import socket
import select
import sys
import threading

from enum import IntEnum
from cstruct2.decorator import Structure, switch, structure
from cstruct2.cstruct2_utils import SocketWrapper


@Structure
class ClientHandshake:
    version: int = 1
    methods_length: int = 1
    methods: int = ["methods_length", 1]


class AuthenticationMethods(IntEnum):
    NoAuthentication = 0
    UsernamePassword = 2


@Structure
class ServerHandshakeResponse:
    version: int = 1
    method: int = 1


class AddressTypes(IntEnum):
    IPv4 = 1
    Domain = 3
    IPv6 = 4


@Structure
class ClientRequest:
    version: int = 1
    command: int = 1
    reserved: int = 1
    address_type: int = 1
    address: switch = switch(
        "address_type",
        {
            AddressTypes.IPv4: (bytes, 4, socket.inet_ntoa),
            AddressTypes.Domain: (str, "pascal", "ascii", socket.gethostbyname),
        },
    )
    port: int = ("big", 2)


@Structure
class ServerResponse:
    version: int = 1
    reply: int = 1
    reserved: int = 1
    address_type: int = 1
    address: bytes = 4
    port: int = ("big", 2)


def handler(client: socket.socket):
    sclient: SocketWrapper = SocketWrapper(client, rw_all=True)
    handshake: dict = ClientHandshake.from_stream(sclient)

    ServerHandshakeResponse.to_stream(
        {"version": 5, "method": AuthenticationMethods.NoAuthentication}, sclient
    )

    request: dict = ClientRequest.from_stream(sclient)

    ServerResponse.to_stream(
        {
            "version": 5,
            "reply": 0,
            "reserved": 0,
            "address_type": AddressTypes.IPv4,
            "address": socket.inet_aton(request["address"]),
            "port": 443,
        },
        sclient,
    )

    other_sock: socket.socket = socket.socket(
        socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
    )
    other_sock.connect((request["address"], request["port"]))

    while True:
        readfds, writefds, excfds = select.select([other_sock, client], [], [])
        try:
            for sock in readfds:
                if sock == client:
                    try:
                        while True:
                            data: bytes = client.recv(4096, socket.MSG_DONTWAIT)
                            other_sock.send(data)
                    except socket.error as e:
                        if e.errno == socket.EWOULDBLOCK:
                            ...
                        else:
                            raise e

                if sock == other_sock:
                    try:
                        while True:
                            data: bytes = other_sock.recv(4096, socket.MSG_DONTWAIT)
                            client.send(data)
                    except socket.error as e:
                        if e.errno == socket.EWOULDBLOCK:
                            continue

                        raise e
        except Exception as err:
            print(str(err))
            return


def main():
    port = 8080
    if sys.argv[1] in ["-p", "--port"]:
        port = int(sys.argv[2])
    else:
        print("Warning: no port explicitly passed in, using the default port of 8080.")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(("0.0.0.0", port))
    sock.listen(64)

    print(f"Hosting SOCKS5 proxy server on port {port}")

    while True:
        client, address = sock.accept()
        print(f"Connection received from: {address[0]}:{address[1]}")
        thr = threading.Thread(target=handler, args=(client,))
        thr.start()


if __name__ == "__main__":
    main()
