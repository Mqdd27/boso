// Package vercel is the API as a Vercel Go function (see /api/index.go at the repo root).
// The web app is served by Vercel itself; the database is Turso, from TURSO_DATABASE_URL and
// TURSO_AUTH_TOKEN (the names the Vercel Turso integration sets).
package vercel

import (
	"log/slog"
	"net/http"
	"os"
	"sync"

	"github.com/Mqdd27/boso/apps/server/internal/db"
	"github.com/Mqdd27/boso/apps/server/internal/httpapi"
)

var (
	mu      sync.Mutex
	handler http.Handler
)

// Handler serves /api/* (one database connection per warm function instance). A failed connect
// is retried on the next request instead of being cached.
func Handler(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	if handler == nil {
		database, err := db.OpenRemote(os.Getenv("TURSO_DATABASE_URL"), os.Getenv("TURSO_AUTH_TOKEN"))
		if err != nil {
			mu.Unlock()
			slog.Error("turso", "err", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte(`{"error":"database"}`))
			return
		}
		handler = httpapi.New(database, nil)
	}
	h := handler
	mu.Unlock()
	h.ServeHTTP(w, r)
}
