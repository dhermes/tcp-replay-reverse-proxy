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

## PostgreSQL

A primary objective of TCP replay is to get a faithful representation of
database load to smoke test changes such as a version upgrade. The `postgres`
package provides tools for parsing a TCP packet as a (client / frontend)
PostgreSQL message.

### Example

```
$ go run ./examples/postgres/main.go --filename ./testdata/postgres.replay.bin
 0: Timestamp=2021-01-21T16:29:12.081079Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.SSLRequest{}
 1: Timestamp=2021-01-21T16:29:12.081528Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.StartupMessage{ProtocolVersion:0x30000, Parameters:map[string]string{"application_name":"psql", "client_encoding":"UTF8", "database":"deployinator", "user":"deployinator_admin"}}
 2: Timestamp=2021-01-21T16:29:12.083771Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.PasswordMessage{Password:"SCRAM-SHA-256"}
 3: Timestamp=2021-01-21T16:29:12.08772Z , Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.SASLResponse{Data:[]uint8{...
 4: Timestamp=2021-01-21T16:29:13.277561Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT n.nspname...
 5: Timestamp=2021-01-21T16:29:14.334422Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid...
 6: Timestamp=2021-01-21T16:29:14.335576Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.relchecks...
 7: Timestamp=2021-01-21T16:29:14.337275Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT a.attname...
 8: Timestamp=2021-01-21T16:29:14.34076Z , Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c2.relname...
 9: Timestamp=2021-01-21T16:29:14.342527Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT pol.polname...
10: Timestamp=2021-01-21T16:29:14.343888Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT oid...
11: Timestamp=2021-01-21T16:29:14.344717Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT pubname...
12: Timestamp=2021-01-21T16:29:14.345484Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid::pg_catalog.regclass...
13: Timestamp=2021-01-21T16:29:14.346175Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid::pg_catalog.regclass...
14: Timestamp=2021-01-21T16:29:14.843417Z, Client=127.0.0.1:64242, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Terminate{}
15: Timestamp=2021-01-21T16:29:18.660011Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.SSLRequest{}
16: Timestamp=2021-01-21T16:29:18.660251Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.StartupMessage{ProtocolVersion:0x30000, Parameters:map[string]string{"application_name":"psql", "client_encoding":"UTF8", "database":"deployinator", "user":"deployinator_admin"}}
17: Timestamp=2021-01-21T16:29:18.662464Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.PasswordMessage{Password:"SCRAM-SHA-256"}
18: Timestamp=2021-01-21T16:29:18.666109Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.SASLResponse{Data:[]uint8{...
19: Timestamp=2021-01-21T16:29:19.853277Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT n.nspname...
20: Timestamp=2021-01-21T16:29:20.958831Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid...
21: Timestamp=2021-01-21T16:29:20.960251Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.relchecks...
22: Timestamp=2021-01-21T16:29:20.961777Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT a.attname...
23: Timestamp=2021-01-21T16:29:20.963873Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c2.relname...
24: Timestamp=2021-01-21T16:29:20.965481Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT pol.polname...
25: Timestamp=2021-01-21T16:29:20.966601Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT oid...
26: Timestamp=2021-01-21T16:29:20.967441Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT pubname...
27: Timestamp=2021-01-21T16:29:20.968249Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid::pg_catalog.regclass...
28: Timestamp=2021-01-21T16:29:20.968895Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Query{String:"SELECT c.oid::pg_catalog.regclass...
29: Timestamp=2021-01-21T16:29:21.685581Z, Client=127.0.0.1:64245, Server=127.0.0.1:5432, PostreSQL Fronted Message=&pgproto3.Terminate{}
```
