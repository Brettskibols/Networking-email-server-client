__author__ = "Brett Jones"

__version__ = "1.0.1"
__status__ = "Development"

import socket
import selectors
import SMTPClientLib
import traceback

clientDebug = None  # Debugger toggle for Dev and guide for possible new user


class NWSThreadedClient:
    def __init__(self, host="127.0.0.1", port=12345):
        if clientDebug:
            print("NWSThreadedClient.__init__", host, port)

        # Network components
        self._host = host
        self._port = port
        self._listening_socket = None
        self._selector = selectors.DefaultSelector()
        self._should_break = False
        self._module = None

    def start_connection(self, host, port):
        addr = (host, port)
        print("starting connection to", addr)
        print("220 " + host + " Simple Mail Transfer Service Ready")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)

        self._module = SMTPClientLib.Module(sock, addr)
        self._module.start()

    def run(self):
        self.start_connection(self._host, self._port)

        while True:
            if self._should_break:

                break
            useraction = input("Enter a command - ")
            self._should_break = not self._module.create_message(useraction)


if __name__ == "__main__":
    client = NWSThreadedClient()
    client.run()
