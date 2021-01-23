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
	"io"
)

// ReplayLogStream parses an input stream of replay log "rows".
type ReplayLogStream struct {
	br *bufio.Reader
}

// NewReplayLogStream produces a ReplayLogStream that wraps a reader.
func NewReplayLogStream(r io.Reader) *ReplayLogStream {
	br := bufio.NewReader(r)
	return &ReplayLogStream{br: br}
}

// Next produces the next parsed `*TCPPacket` in the stream.
func (rls *ReplayLogStream) Next() (*TCPPacket, error) {
	tp := &TCPPacket{}
	n, err := tp.Read(rls.br)
	if err == io.EOF && n != 0 {
		return nil, io.ErrUnexpectedEOF
	}

	if err != nil {
		return nil, err
	}

	return tp, nil
}
