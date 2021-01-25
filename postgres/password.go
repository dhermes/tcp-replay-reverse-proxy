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
	"encoding/binary"

	"github.com/jackc/pgproto3/v2"
)

// NOTE: Ensure that
//       - `PasswordMessage` satisfies `pgproto3.FrontendMessage`
var (
	_ pgproto3.FrontendMessage = (*PasswordMessage)(nil)
)

// PasswordMessage is a stand-in for the four different message formats, all
// of which have `'p'` as `Byte1`:
// - GSSResponse
// - PasswordMessage
// - SASLInitialResponse
// - SASLResponse
type PasswordMessage struct {
	Data string
}

// Frontend identifies this message as sendable by a PostgreSQL frontend.
func (*PasswordMessage) Frontend() {}

// Decode decodes src into `dst`. `src` must contain the complete message with
// the exception of the initial 1 byte message type identifier and 4 byte
// message length.
func (pm *PasswordMessage) Decode(src []byte) error {
	pm.Data = string(src)
	return nil
}

// Encode encodes `src` into `dst`. `dst` will include the 1 byte message type
// identifier and the 4 byte message length.
func (pm *PasswordMessage) Encode(dst []byte) []byte {
	dst = append(dst, 'p')
	// Write 4 empty bytes so we can populate them with the length header
	index := len(dst)
	dst = append(dst, 0, 0, 0, 0)
	dataBytes := []byte(pm.Data)
	binary.BigEndian.PutUint32(dst[index:], uint32(4+len(dataBytes)))
	// Write the actual data.
	dst = append(dst, dataBytes...)
	return dst
}
