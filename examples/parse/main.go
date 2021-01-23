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

package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"

	"github.com/dhermes/tcp-replay-reverse-proxy/parse"
)

func runParse(filename string) error {
	binFile, err := filepath.Abs(filename)
	if err != nil {
		return err
	}

	f, err := os.Open(binFile)
	if err != nil {
		return err
	}
	defer f.Close()

	rls := parse.NewReplayLogStream(f)
	tp, err := rls.Next()
	i := 0

	for err == nil {
		fmt.Printf(
			"%2d: Timestamp=%-27s, Client=%s, Server=%s, len(Chunk)=%d\n",
			i, tp.Timestamp.Format(time.RFC3339Nano),
			tp.ClientAddr, tp.ServerAddr, len(tp.Chunk),
		)
		i++
		tp, err = rls.Next()
	}

	if err == io.EOF {
		return nil
	}

	return err
}

func run() error {
	filename := ""
	rootCmd := &cobra.Command{
		Use:           "parse-example",
		Short:         "Run example that demonstrates usage of `parse` package",
		SilenceErrors: true,
		SilenceUsage:  true,
		RunE: func(_ *cobra.Command, _ []string) error {
			return runParse(filename)
		},
	}

	rootCmd.PersistentFlags().StringVar(
		&filename, "filename", "", "Filename containing `*.replay.bin` file",
	)
	rootCmd.MarkPersistentFlagRequired("filename")

	return rootCmd.Execute()
}

func main() {
	err := run()
	if err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(1)
	}
}
