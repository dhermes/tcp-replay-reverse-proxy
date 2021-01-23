// Package server provides an implementation for a pluggable capturing reverse
// proxy server.
//
// The primary goal of the reverse proxy server is the shuttle TCP packets from
// a downstream client to an upstream server. However, the intent is to capture
// each TCP packet with accompanying metadata about the timestamp and an
// identifier for the socket. Packets (with metadata) will be sent to a
// channel; consumer(s) of this channel will persist the packets without
// blocking the proxied connection.
//
// It is designed to be pluggable so that
// - Each new connection **to** the proxy server can be wrapped so that things
//   like parsing PROXY protocol headers or unwrapping the content of a TLS
//   connection (by terminating TLS directly)
// - Each new connection **to** the upstream server can be wrapped as well,
//   so that TCP packets can be written into a raw TCP socket, a TLS socket or
//   any other abstraction
// - The consumer of the channel with TCP packets can be customized to write
//   to disk, send packets over the network, etc.
// - Minimally invasive metrics and tracing can be added as needed
package server
