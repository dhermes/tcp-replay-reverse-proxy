# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import socket
import threading
import time

import _buffer
import _display


def _maybe_log_line(log_queue, tcp_chunk, client_socket, server_socket):
    """Sent a log line to the log queue, if set.

    Args:
        log_queue (Optional[queue.Queue]): The queue where log lines will be
            pushed, or :data:`None`.
        tcp_chunk (bytes): Chunk of data that was proxied.
        client_socket (socket.socket): The client socket.
        server_socket (socket.socket): The server socket.
    """
    if log_queue is None:
        return

    log_queue.put((time.time_ns(), tcp_chunk, client_socket, server_socket))


def redirect_socket(recv_socket, send_socket, description, log_queue):
    """Redirect a TCP stream from one socket to another.

    This only redirects in **one** direction, i.e. it RECVs from
    ``recv_socket`` and SENDs to ``send_socket``.

    Args:
        recv_socket (socket.socket): The socket that will be RECV-ed from.
        send_socket (socket.socket): The socket that will be SENT to.
        description (str): A description of the RECV->SEND relationship for
            this socket pair.
        log_queue (Optional[queue.Queue]): The queue where log lines will be
            pushed, or :data:`None`.
    """
    tcp_chunk = _buffer.recv(recv_socket, send_socket)
    while tcp_chunk != b"":
        _maybe_log_line(log_queue, tcp_chunk, recv_socket, send_socket)

        _buffer.send(send_socket, tcp_chunk)
        # Read the next chunk from the socket.
        tcp_chunk = _buffer.recv(recv_socket, send_socket)

    _display.display(f"Done redirecting socket for {description}")
    recv_socket.close()


def connect_socket_pair(
    log_queue, client_socket, client_addr, server_host, server_port
):
    """Connect two socket pairs for bidirectional RECV<->SEND.

    Since calls to RECV (both on the client and the server sockets) can block,
    this will spawn two threads that simultaneously read (via RECV) from one
    socket and write (via SEND) into the other socket.

    Args:
        log_queue (queue.Queue): The queue where log lines will be pushed.
        client_socket (socket.socket): An already open socket from a client
            that has made a request directly to a running
            ``tcp-replay-reverse-proxy`` proxy.
        client_addr (str): The address of the client socket; used for printing
            information about the connection. Note that
            ``client_socket.getsockname()`` could be used directly to recover
            this information.
        server_host (str): The host name where the "server" process is running
            (i.e. the server that is being proxied).
        server_port (int): A port number for a running "server" process.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # See: https://docs.python.org/3/library/socket.html#timeouts-and-the-accept-method
    server_socket.setblocking(0)
    indicator = server_socket.connect_ex((server_host, server_port))
    if indicator not in (0, errno.EINPROGRESS):
        err_name = errno.errorcode.get(indicator, "UNKNOWN")
        raise BlockingIOError(indicator, f"Error: {err_name}")

    server_addr = f"{server_host}:{server_port}"
    read_description = f"client({client_addr})->proxy->server({server_addr})"
    # Only log the lines sent **to** the server.
    t_read = threading.Thread(
        target=redirect_socket,
        args=(client_socket, server_socket, read_description, log_queue),
    )
    write_description = f"server({server_addr})->proxy->client({client_addr})"
    t_write = threading.Thread(
        target=redirect_socket,
        args=(server_socket, client_socket, write_description, None),
    )

    t_read.start()
    t_write.start()

    t_read.join()
    t_write.join()
