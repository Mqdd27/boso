// Root module only for the Vercel Go function in api/ (Vercel needs go.mod at the project root).
// The server itself is the apps/server module.
module github.com/Mqdd27/boso

go 1.27.3

require github.com/Mqdd27/boso/apps/server v0.0.0

require (
	github.com/antlr4-go/antlr/v4 v4.13.1 // indirect
	github.com/coder/websocket v1.8.15 // indirect
	github.com/dustin/go-humanize v1.1.0 // indirect
	github.com/google/uuid v1.6.0 // indirect
	github.com/mattn/go-isatty v0.0.24 // indirect
	github.com/mfridman/interpolate v0.2.0 // indirect
	github.com/ncruces/go-strftime v1.1.0 // indirect
	github.com/pressly/goose/v3 v3.30.1 // indirect
	github.com/remyoudompheng/bigfft v0.0.0-20230129092748-24d4a6f8daec // indirect
	github.com/sethvargo/go-retry v0.5.0 // indirect
	github.com/tursodatabase/libsql-client-go v0.0.0-20260528064733-9d5d30a29a60 // indirect
	go.uber.org/multierr v1.11.0 // indirect
	golang.org/x/crypto v0.59.0 // indirect
	golang.org/x/exp v0.0.0-20261109185158-a52e3aef5920 // indirect
	golang.org/x/sync v0.25.0 // indirect
	golang.org/x/sys v0.50.0 // indirect
	modernc.org/libc v1.80.2 // indirect
	modernc.org/mathutil v1.7.1 // indirect
	modernc.org/memory v1.12.1 // indirect
	modernc.org/sqlite v1.62.0 // indirect
)

replace github.com/Mqdd27/boso/apps/server => ./apps/server
