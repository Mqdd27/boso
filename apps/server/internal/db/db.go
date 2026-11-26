// Package db opens the SQLite database and applies migrations.
package db

import (
	"context"
	"database/sql"
	"embed"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/pressly/goose/v3"
	_ "github.com/tursodatabase/libsql-client-go/libsql" // registers "libsql" (remote Turso)
	_ "modernc.org/sqlite"                               // registers "sqlite" (local file)
)

//go:embed migrations/*.sql
var migrations embed.FS

// Open opens (or creates) dataDir/boso.db and migrates it to the latest version.
func Open(dataDir string) (*sql.DB, error) {
	if err := os.MkdirAll(dataDir, 0o750); err != nil {
		return nil, fmt.Errorf("create data dir: %w", err)
	}
	dsn := "file:" + filepath.Join(dataDir, "boso.db") +
		"?_pragma=journal_mode(WAL)&_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if err := migrate(db); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

// OpenRemote opens a Turso (libSQL) database by URL and auth token and migrates it. Used on
// Vercel, where there is no disk. Same schema and SQL as the local file.
func OpenRemote(url, token string) (*sql.DB, error) {
	// libsql:// would use a WebSocket, which drops mid-migration on serverless ("stream is
	// closed"); https:// is stateless HTTP against the same database.
	url = strings.Replace(url, "libsql://", "https://", 1)
	db, err := sql.Open("libsql", url+"?authToken="+token)
	if err != nil {
		return nil, fmt.Errorf("open turso: %w", err)
	}
	// ponytail: migrates on every cold start without a lock; two cold starts racing a new
	// migration could collide. Fine at this size; run migrations from CI if it ever matters.
	if err := migrate(db); err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func migrate(db *sql.DB) error {
	dir, err := fs.Sub(migrations, "migrations")
	if err != nil {
		return fmt.Errorf("migrations dir: %w", err)
	}
	provider, err := goose.NewProvider(goose.DialectSQLite3, db, dir)
	if err != nil {
		return fmt.Errorf("goose provider: %w", err)
	}
	if _, err := provider.Up(context.Background()); err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}
