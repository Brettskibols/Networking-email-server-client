import sys
import selectors
import queue
import json
import io
import struct
import traceback
import SMTPClientEncryption
from threading import Thread
import time


class Module(Thread):
    def __init__(self, sock, addr):
        Thread.__init__(self)

        self._selector = selectors.DefaultSelector()
        self._sock = sock
        self._addr = addr
        self._incoming_buffer = queue.Queue()
        self._outgoing_buffer = queue.Queue()
        self._is_closed = False
        self.encryption = SMTPClientEncryption.nws_encryption()
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self._selector.register(self._sock, events, data=None)

    def run(self):
        try:
            while True:
                try:
                    events = self._selector.select(timeout=1)
                except OSError:

                    self._sock.close()
                    self._is_closed = True
                    break

                for key, mask in events:
                    message = key.data
                    try:
                        if mask & selectors.EVENT_READ:
                            self._read()
                        if mask & selectors.EVENT_WRITE and not self._outgoing_buffer.empty():
                            self._write()
                    except Exception:
                        # print(
                        #     "main: error: exception for",
                        #     f"{self._addr}:\n{traceback.format_exc()}",
                        # )

                        self._sock.close()
                        self._is_closed = True
                        break
                # Check for a socket being monitored to continue.
                if not self._selector.get_map():
                    break
        finally:
            self._clear()
            self._selector.close()

    def _read(self):
        try:
            data = self._sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._incoming_buffer.put(self.encryption.decrypt(data.decode()))
            else:
                raise RuntimeError("Peer closed.")

        self._process_response()

    def _write(self):
        try:
            message = self._outgoing_buffer.get_nowait()
        except:
            message = None

        if message:
            print("sending", repr(message), "to", self._addr)
            try:
                sent = self._sock.send(message)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass

    def create_message(self, content):
        if self._is_closed:
            return False
        encoded = self.encryption.encrypt(content)
        nwencoded = encoded.encode()
        self._outgoing_buffer.put(nwencoded)
        return not self._is_closed

    def _clear(self):
        print("221 Service closing transmission channel")
        print("Connection closed with remote host...")   # Informs the user the connection is ending
        while not self._incoming_buffer.empty():
            self._process_response()

    def _process_response(self):
        message = self._incoming_buffer.get()
        header_length = 3
        if len(message) >= header_length:
            print(message[0:header_length], message[header_length:])
        print("Processing thing")
        if '221' in message[0:3]:  # Attempts to catch 221 in message but connection may have ended
            print(message)         # at this point making this impossible
            # time.sleep(2)
            try:
                self.close()
            except OSError as exc:        # Avoids error exception
                pass  # do nothing
        if '214' in message[0:3]:
            print("Enter a command")

    def close(self):
        print("closing connection to", self._addr)  # Might be able to make a method / function shared client/srv lib
        try:
            self._selector.unregister(self._sock)
        except Exception as e:
            print(
                f"error: selector.unregister() exception for",
                f"{self._addr}: {repr(e)}",
            )
        try:
            self._sock.close()
        except OSError as e:
            print(
                f"error: socket.close() exception for",
                f"{self._addr}: {repr(e)}",
            )
        finally:
            # Delete reference to socket object for garbage collection
            self._sock = None
