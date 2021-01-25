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

package postgres

import (
	"bytes"
	"encoding/binary"
	"fmt"

	"github.com/jackc/pgproto3/v2"
)

var (
	postgresProtocolVersion = []byte{'\x00', '\x03', '\x00', '\x00'}
	cancelRequestPrefix     = bigEndianPackUint32(8, 80877102)
	sslRequest              = bigEndianPackUint32(8, 80877103)
	gssEncReq               = bigEndianPackUint32(8, 80877104)
)

// ParseChunk parses a TCP packet as a PostgreSQL packet. This assumes a
// discrete TCP packet contains exactly one PostgreSQL packet, but this
// assumption may be revisted at a later time.
//
// See:
// - https://godoc.org/github.com/jackc/pgproto3
// - https://www.postgresql.org/docs/13/protocol-message-formats.html
func ParseChunk(chunk []byte) (pgproto3.FrontendMessage, error) {
	fm, err := parseFrontendMessage(chunk)
	if err != nil {
		return nil, err
	}

	if fm != nil {
		return fm, nil
	}

	if len(chunk) == 0 {
		err := fmt.Errorf(
			"%w; message must contain at least 8 bytes, has %d",
			ErrParsingClientMessage, len(chunk),
		)
		return nil, err
	}

	if bytes.Equal(chunk[:8], cancelRequestPrefix) {
		cr := &pgproto3.CancelRequest{}
		err = cr.Decode(chunk[4:])
		if err != nil {
			return nil, err
		}

		return cr, nil
	}

	if bytes.Equal(chunk[:8], sslRequest) {
		sr := &pgproto3.SSLRequest{}
		return sr, nil
	}

	if bytes.Equal(chunk[:8], gssEncReq) {
		ger := &pgproto3.GSSEncRequest{}
		return ger, nil
	}

	if !bytes.Equal(chunk[4:8], postgresProtocolVersion) {
		err = fmt.Errorf("%w; expected a startup message", ErrParsingClientMessage)
		return nil, err
	}

	sm := &pgproto3.StartupMessage{}
	err = sm.Decode(chunk[4:])
	if err != nil {
		return nil, err
	}

	return sm, nil
}

func parseFrontendMessage(chunk []byte) (pgproto3.FrontendMessage, error) {
	if len(chunk) < 5 {
		err := fmt.Errorf(
			"%w; message must contain at least 5 bytes, has %d",
			ErrParsingClientMessage, len(chunk),
		)
		return nil, err
	}

	messageType := chunk[0]
	switch messageType {
	case 'B':
		b := &pgproto3.Bind{}
		err := b.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return b, nil
	case 'C':
		c := &pgproto3.Close{}
		err := c.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return c, nil
	case 'd':
		cd := &pgproto3.CopyData{}
		err := cd.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return cd, nil
	case 'c':
		cd := &pgproto3.CopyDone{}
		err := cd.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return cd, nil
	case 'f':
		cf := &pgproto3.CopyFail{}
		err := cf.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return cf, nil
	case 'D':
		d := &pgproto3.Describe{}
		err := d.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return d, nil
	case 'E':
		e := &pgproto3.Execute{}
		err := e.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return e, nil
	case 'H':
		f := &pgproto3.Flush{}
		err := f.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return f, nil
	case 'F':
		err := fmt.Errorf("%w; FunctionCall not supported by `pgx` project", ErrNotImplemented)
		return nil, err
	case 'P':
		p := &pgproto3.Parse{}
		err := p.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return p, nil
	case 'Q':
		q := &pgproto3.Query{}
		err := q.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return q, nil
	case 'S':
		s := &pgproto3.Sync{}
		err := s.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return s, nil
	case 'X':
		t := &pgproto3.Terminate{}
		err := t.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return t, nil
	case 'p':
		bm := &Byte1pMessage{}
		err := bm.Decode(chunk[5:])
		if err != nil {
			return nil, err
		}

		return bm, nil
	default:
		return nil, nil
	}
}

func bigEndianPackUint32(v ...uint32) []byte {
	b := make([]byte, 4*len(v))
	for i, element := range v {
		binary.BigEndian.PutUint32(b[4*i:4*(i+1)], element)
	}
	return b
}
