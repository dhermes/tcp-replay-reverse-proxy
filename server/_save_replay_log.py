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


import base64
import datetime
import queue


# Block a `get()` from the queue for 2 seconds.
QUEUE_GET_TIMEOUT = 2.0
QUEUE_EMPTY = object()  # Sentinel


def _queue_get(queue_, timeout):
    try:
        return queue_.get(block=True, timeout=timeout)
    except queue.Empty:
        return QUEUE_EMPTY


def save_log_worker(filename, log_queue, done_event):
    """Worker to save log messages from a queue to a file.

    This is intended to be launched in a thread to avoid blocking socket
    I/O with the requisite file I/O.

    Args:
        filename (pathlib.Path): The file where the replay log will be written.
        log_queue (queue.Queue): The queue where log lines will be pushed.
        done_event (threading.Event): An event indicating the proxy that is
            generating log lines is done.
    """
    with open(filename, "wb") as file_obj:
        while True:
            if done_event.is_set() and log_queue.empty():
                return

            value = _queue_get(log_queue, QUEUE_GET_TIMEOUT)
            if value is QUEUE_EMPTY:
                continue

            # NOTE: We assume items in the queue are of type
            #       `Tuple[datetime.datetime, bytes, str]`.
            timestamp, tcp_chunk, description = value
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)

            ts_str = timestamp.isoformat()
            ts_bytes = ts_str.encode("ascii")
            # NOTE: This **assumes**, but does not check, that `description`
            #       does not contain a `|`.
            log_line = (
                ts_bytes
                + b"|"
                + description.encode("ascii")
                + b"|"
                + base64.b64encode(tcp_chunk)
                + b"\n"
            )
            file_obj.write(log_line)
