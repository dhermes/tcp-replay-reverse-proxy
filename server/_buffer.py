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

import select


SELECT_TIMEOUT = 0.05


def is_closed(socket_):
    """Determine if a socket is closed.

    This uses the associated file descriptor as a proxy for "closed".

    Args:
        socket_ (socket.socket): The socket to check.

    Returns:
        bool: Indicates if closed or open.
    """
    return socket_.fileno() == -1


def wait_readable(recv_socket, send_socket):
    """Wait until a non-blocking socket is readable.

    Args:
        recv_socket (socket.socket): A socket to RECV from.
        send_socket (socket.socket): A socket connected (on the "other end") to
            ``recv_socket``.

    Returns:
        Optional[socket.socket]: Either ``recv_socket`` if the connection is
        still open or :data:`None`.

    Raises:
        ValueError: If ``recv_socket`` is not readable after
            ``select.select()`` returns.
    """
    while True:
        readable, _, _ = select.select([recv_socket], [], [], SELECT_TIMEOUT)
        if readable:
            break
        # If the "other end" of the socket is closed, ``recv_socket`` is done.
        if is_closed(send_socket):
            return None

    if readable != [recv_socket]:
        raise ValueError("Socket not ready to RECV")

    return recv_socket


def recv(recv_socket, send_socket, buffer_size=0x10000):
    """Call ``recv()`` on a socket; with some extra checks.

    This **assumes** ``recv_socket`` is non-blocking, so a **blocking** call to
    ``select.select()`` with a timoeut is used to wait until the socket is
    ready. Additionally, the ``send_socket`` is used to determine if the
    connection has been closed.

    .. note::

        Rather than using the negotiated connection (e.g.
        ``SETTINGS_MAX_FRAME_SIZE``) to set the buffer size, we just use a
        best guess of something "large enough" to make sure that each frame
        fits in this size.

        If a RECV returns a chunk from the TCP stream **equal** to the buffer
        size, we interpret this as an "incomplete" frame and throw a cowardly
        exception. A more robust implementation could try to make subsequent
        ``recv()`` calls to see if the chunk is an entire frame.

    Args:
        recv_socket (socket.socket): A socket to RECV from.
        send_socket (socket.socket): A socket connected (on the "other end") to
            ``recv_socket``.
        buffer_size (Optional[int]): The size of the read.

    Returns:
        bytes: The chunk that was read from the TCP stream.

    Raises:
        RuntimeError: If the TCP chunk returned is "full size" (i.e. has
            ``buffer_size`` bytes).
    """
    recv_socket = wait_readable(recv_socket, send_socket)
    if recv_socket is None:
        # Indicates the "other end" of the socket is closed, so we
        # simulate an empty RECV.
        return b""

    tcp_chunk = recv_socket.recv(buffer_size)
    if len(tcp_chunk) == buffer_size:
        raise RuntimeError(
            "TCP RECV() may not have captured entire message frame"
        )

    return tcp_chunk


def send(send_socket, tcp_chunk):
    """Call ``send()`` on a socket; with some extra checks.

    .. note::

        This throws a cowardly exception if the entire ``tcp_chunk`` cannot be
        sent in a single SND. A more robust implementation could try to make
        subsequent ``send()`` calls or just use ``sendall()``.

    Args:
        send_socket (socket.socket): A socket to SEND to.
        tcp_chunk (bytes): A chunk to send to the socket.

    Raises:
        RuntimeError: If SEND returns a length other than the size of
            ``tcp_chunk``.
    """
    bytes_sent = send_socket.send(tcp_chunk)
    if bytes_sent != len(tcp_chunk):
        raise RuntimeError("Not all bytes were sent")
