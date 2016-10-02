from poker import Channel, ChannelError, MessageFormatError, MessageTimeout
import gevent
import errno
import json
import socket
import time


class ChannelSocket(Channel):
    def __init__(self, socket, address, logger=None):
        self._socket = socket
        self._address = address
        self._socket.setblocking(False)

    def close(self):
        self._socket.close()

    def send_message(self, message):
        # Encode the message
        msg_serialized = json.dumps(message)
        msg_encoded = msg_serialized.encode("utf-8")

        msg_len = str(len(msg_encoded)) + "\n"
        msg_len_encoded = msg_len.encode("utf-8")

        try:
            # Sends message length
            self._socket.send(msg_len_encoded)
            # Sends the message
            self._socket.sendall(msg_encoded)
        except:
            raise ChannelError("Unable to send data to the remote host")

    def _recv(self, size, timeout_epoch):
        message = b''
        while not timeout_epoch or time.time() < timeout_epoch:
            try:
                message += self._socket.recv(size)
                if len(message) >= size:
                    return message
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    # Wait for 200 milliseconds
                    gevent.sleep(0.2)
                    continue
                else:
                    raise ChannelError("Unable to receive data from the remote host")
        raise MessageTimeout("Timed out")

    def _recv_message_len(self, time_timeout):
        message = b''
        while not time_timeout or time.time() < time_timeout:
            chr = self._recv(1, time_timeout)
            if chr == b'\n':
                try:
                    return int(message.decode("utf-8"))
                except ValueError:
                    raise MessageFormatError(desc="Unable to receive the JSON message")
            else:
                message += chr
        raise MessageTimeout("Timed out")

    def recv_message(self, timeout_epoch=None):
        # Read the json message size
        msg_len = self._recv_message_len(timeout_epoch)

        # Read and decode the json message
        encoded = self._recv(msg_len, timeout_epoch)
        serialized = encoded.decode("utf-8")

        try:
            # Deserialize and return the message
            return json.loads(serialized)
        except ValueError:
            # Invalid json
            raise MessageFormatError(desc="Unable to decode the JSON message")