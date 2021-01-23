// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package parse

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"strconv"
	"time"
)

// TCPPacket represents a "row" from a replay file containing a TCP packet
// and associated metadata.
type TCPPacket struct {
	Timestamp  time.Time
	ClientAddr Addr
	ServerAddr Addr
	Chunk      []byte
}

// Read reads and parses the next "row" in a replay log into the
// current receiver.
func (tp *TCPPacket) Read(br *bufio.Reader) (bytesRead int, err error) {
	var tsBytes [8]byte
	n, err := io.ReadFull(br, tsBytes[:])
	bytesRead += n
	if err != nil {
		return
	}

	tsNanos := binary.BigEndian.Uint64(tsBytes[:])
	sec := tsNanos / 1_000_000_000
	nsec := tsNanos % 1_000_000_000
	tp.Timestamp = time.Unix(int64(sec), int64(nsec)).UTC()

	clientAddrBytes, err := br.ReadBytes(' ')
	bytesRead += len(clientAddrBytes)
	if err != nil {
		return
	}
	// Parse everything except for the `' '` at the end.
	clientAddr, err := NewAddr(clientAddrBytes[:len(clientAddrBytes)-1])
	if err != nil {
		return
	}
	tp.ClientAddr = *clientAddr

	serverAddrBytes, err := br.ReadBytes(' ')
	bytesRead += len(serverAddrBytes)
	if err != nil {
		return
	}
	// Parse everything except for the `' '` at the end.
	serverAddr, err := NewAddr(serverAddrBytes[:len(serverAddrBytes)-1])
	if err != nil {
		return
	}
	tp.ServerAddr = *serverAddr

	var sizeHeader [4]byte
	n, err = io.ReadFull(br, sizeHeader[:])
	bytesRead += n
	if err != nil {
		return
	}

	chunkSize := int(binary.BigEndian.Uint32(sizeHeader[:]))
	tp.Chunk = make([]byte, chunkSize)
	n, err = io.ReadFull(br, tp.Chunk)
	bytesRead += n
	if err != nil {
		return
	}

	return
}

// Addr represents a basic `{IP}:{PORT}` address.
type Addr struct {
	IP   net.IP
	Port uint16
}

// NewAddr parses a bytestring into an address, if possible.
func NewAddr(b []byte) (*Addr, error) {
	host, portStr, err := net.SplitHostPort(string(b))
	if err != nil {
		return nil, err
	}

	ip := net.ParseIP(host)
	if ip == nil {
		return nil, fmt.Errorf("%w; Host=%q", ErrParsingIP, host)
	}

	port, err := strconv.ParseUint(portStr, 10, 16)
	if err != nil {
		return nil, err
	}

	return &Addr{IP: ip, Port: uint16(port)}, nil
}

// String converts an address to a string.
func (a Addr) String() string {
	return fmt.Sprintf("%s:%d", a.IP, a.Port)
}
