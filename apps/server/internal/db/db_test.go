package db

import "testing"

func TestOpenMigrates(t *testing.T) {
	dir := t.TempDir()
	for i := range 2 { // second open must be a no-op migration
		db, err := Open(dir)
		if err != nil {
			t.Fatalf("open #%d: %v", i, err)
		}
		if _, err := db.Exec(`INSERT OR REPLACE INTO meta (key, value) VALUES ('k', 'v')`); err != nil {
			t.Fatalf("meta table missing: %v", err)
		}
		db.Close()
	}
}
