package main

import (
	"crypto/sha256"
	"crypto/tls"
	"fmt"
)

func main() {
	h := sha256.New()
	h.Write([]byte("hello fips"))
	fmt.Printf("SHA-256: %x\n", h.Sum(nil))

	cfg := &tls.Config{MinVersion: tls.VersionTLS12}
	fmt.Printf("TLS MinVersion: %d\n", cfg.MinVersion)

	fmt.Println("OK")
}
