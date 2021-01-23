# TCP Replay Reverse Proxy

> Capturing Reverse Proxy Written In Go with tools for Traffic Replay

## Replay File Format

The replay file is intended to require minimal processing when writing. It
is composed of a series of TCP packets (as chunks) along with metadata.
A length header is used for the the TCP packet so there is no need for a
delimiter between "rows" in the replay file.

A given row will be of the form

```
[TIMESTAMP][CLIENT ADDRESS] [SERVER ADDRESS] [LENGTH][TCP PACKET]
```

where the second and third values are terminated by a space character (`\x20`)
which is unambiguous because the client and server addressed can only contain
IPv4 / IPv6 addresses and a port.

-   `TIMESTAMP`: 8 bytes, `unsigned int64` with big-endian encoding of the
    number of nanoseconds since the Unix epoch. For example the timestamp
    `2021-01-21T16:29:21.685581Z` is `1611246561685581000` nanoseconds after
    the epoch, which can be encoded as
    `\x16 \x5c \x4c \x36 \x0a \xd6 \xac \xc8`
-   `CLIENT ADDRESS`: Variable length, the IPv4 / IPv6 address and port of the
    connection's client, for example `127.0.0.1:64245`; this is ASCII
    encoded and will terminate at a space character (`\x20`)
-   `SERVER ADDRESS`: Variable length, the IPv4 / IPv6 address and port of the
    connection's server, for example `127.0.0.1:5432`; this is ASCII
    encoded and will terminate at a space character (`\x20`)
-   `LENGTH`: 4 bytes, `unsigned int32` with big-endian encoding of the
    length of the TCP packet
-   `TCP PACKET`: `LENGTH` bytes, the TCP packet that was captured

### Example

```
$ go run ./examples/parse/main.go --filename ./testdata/postgres.replay.bin
 0: Timestamp=2021-01-21T16:29:12.081079Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, len(Chunk)=8
 1: Timestamp=2021-01-21T16:29:12.081528Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, len(Chunk)=98
...
28: Timestamp=2021-01-21T16:29:20.968895Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, len(Chunk)=314
29: Timestamp=2021-01-21T16:29:21.685581Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, len(Chunk)=5
```
