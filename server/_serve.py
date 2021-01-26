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

import queue
import select
import socket
import threading
import time

import _connect
import _display
import _keepalive
import _save_replay_log


PROXY_HOST = "0.0.0.0"
BACKLOG = 5
KEEP_ALIVE_INTERVAL = 180  # 3 minutes, in seconds
# Number of log lines to write before puts to queue will block
QUEUE_BUFFER = 256


def accept(non_blocking_socket):
    """Accept a connection on a non-blocking socket.

    Since the socket is non-blocking, a **blocking** call to
    ``select.select()`` is used to wait until the socket is ready.

    Args:
        non_blocking_socket (socket.socket): A socket that will block to accept
            a connection.

    Returns:
       Tuple[socket.socket, str]: A pair of:
       * The socket of the client connection that was accepted
       * The address (IP and port) of the client socket

    Raises:
        ValueError: If ``non_blocking_socket`` is not readable after
            ``select.select()`` returns.
    """
    readable, _, _ = select.select([non_blocking_socket], [], [])
    if readable != [non_blocking_socket]:
        raise ValueError("Socket not ready to accept connections")

    client_socket, (ip_addr, port) = non_blocking_socket.accept()
    # See: https://docs.python.org/3/library/socket.html#timeouts-and-the-accept-method
    client_socket.setblocking(0)
    # Turn on KEEPALIVE for the connection.
    _keepalive.set_keepalive(client_socket, KEEP_ALIVE_INTERVAL)

    client_addr = f"{ip_addr}:{port}"
    return client_socket, client_addr


def _serve_proxy(all_threads, log_queue, proxy_port, server_host, server_port):
    """Serve the proxy.

    This is a "happy path" implementation for ``serve_proxy`` that doesn't
    worry about interrupt handling (e.g. ``KeyboardInterrupt``).

    Args:
        all_threads (List[threading.Thread]): A list of threads to append to.
            We utilize the fact that `list.append()` is thread-safe in Python.
        log_queue (queue.Queue): The queue where log lines will be pushed.
        proxy_port (int): A legal port number that the caller has permissions
            to bind to.
        server_host (str): The host name where the server process is
            running (i.e. the server that is being proxied).
        server_port (int): A port number for a running "server" process.
    """
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setblocking(0)
    proxy_socket.bind((PROXY_HOST, proxy_port))
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.listen(BACKLOG)
    _display.display(
        "Starting tcp-replay-reverse-proxy proxy server on port "
        f"{proxy_port}\n  Proxying server located at "
        f"{server_host}:{server_port}"
    )

    while True:
        client_socket, client_addr = accept(proxy_socket)
        _display.display(f"Accepted connection from {client_addr}")
        # NOTE: Nothing actually `.join()`-s this thread.
        t_handle = threading.Thread(
            target=_connect.connect_socket_pair,
            args=(
                log_queue,
                client_socket,
                client_addr,
                server_host,
                server_port,
            ),
        )
        t_handle.start()
        all_threads.append(t_handle)


def serve_proxy(*, proxy_port, server_host, server_port, replay_log):
    """Serve the proxy.

    This should run as a top-level server and CLI invocations of
    ``tcp-replay-reverse-proxy`` will directly invoke it.

    Args:
        proxy_port (int): A legal port number that the caller has permissions
            to bind to.
        server_host (Optional[str]): The host name where the server process is
            running (i.e. the server that is being proxied).
        server_port (int): A port number for a running "server" process.
        replay_log (pathlib.Path): The file where the replay log will be
            written.
    """
    # TODO: Limit the size of the thread pool.
    #       e.g. see
    #       https://github.com/dhermes/tcp-h2-describe/blob/73c135b37550858c322b7b67c84333381afd3c69/src/tcp_h2_describe/_serve.py#L105
    done_event = threading.Event()
    log_queue = queue.Queue(maxsize=QUEUE_BUFFER)
    save_log_thread = threading.Thread(
        target=_save_replay_log.save_log_worker,
        args=(replay_log, log_queue, done_event),
    )
    save_log_thread.start()
    all_threads = [save_log_thread]

    try:
        _serve_proxy(
            all_threads, log_queue, proxy_port, server_host, server_port
        )
    except KeyboardInterrupt:
        _display.display(
            "Stopping tcp-replay-reverse-proxy proxy server "
            f"on port {proxy_port}"
        )
        _display.display("Waiting for request handlers to complete...")
        done_event.set()
        # TODO: Add thread shutdown (possibly via a `threading.Event`) instead
        #       of just waiting for each socket to be closed.
        for t_handle in all_threads:
            t_handle.join()
