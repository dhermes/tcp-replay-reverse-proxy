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

"""
Provides an implementation for a pluggable capturing reverse proxy server.

The primary goal of the reverse proxy server is to shuttle TCP packets from
a downstream client to an upstream server. However, the intent is to capture
each TCP packet with accompanying metadata about the timestamp and an
identifier for the socket. Packets (with metadata) will be sent to a
channel; consumer(s) of this channel will persist the packets without
blocking the proxied connection.

It is designed to be pluggable so that
- Each new connection **to** the proxy server can be wrapped so that things
  like parsing PROXY protocol headers or unwrapping the content of a TLS
  connection (by terminating TLS directly)
- Each new connection **to** the upstream server can be wrapped as well,
  so that TCP packets can be written into a raw TCP socket, a TLS socket or
  any other abstraction
- The consumer of the channel with TCP packets can be customized to write
  to disk, send packets over the network, etc.
- Minimally invasive metrics and tracing can be added as needed
"""
