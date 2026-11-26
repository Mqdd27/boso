// Package vercel is the API as a Vercel Go function (see /api/index.go at the repo root).
// The web app is served by Vercel itself; the database is Turso, from TURSO_DATABASE_URL and
// TURSO_AUTH_TOKEN (the names the Vercel Turso integration sets).
package vercel

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strings"
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
		url, token := os.Getenv("TURSO_DATABASE_URL"), os.Getenv("TURSO_AUTH_TOKEN")
		database, err := db.OpenRemote(url, token)
		if err != nil {
			mu.Unlock()
			slog.Error("turso", "err", err)
			// TODO(debug): remove "detail" once Turso works on Vercel. The token is redacted.
			detail := err.Error()
			if token != "" {
				detail = strings.ReplaceAll(detail, token, "***")
			}
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			_ = json.NewEncoder(w).Encode(map[string]any{
				"error": "database", "detail": detail, "url_set": url != "", "token_set": token != "",
			})
			return
		}
		handler = httpapi.New(database, nil)
	}
	h := handler
	mu.Unlock()
	h.ServeHTTP(w, r)
}
