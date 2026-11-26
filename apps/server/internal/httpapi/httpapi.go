// Package httpapi wires the HTTP routes.
package httpapi

import (
	"database/sql"
	"io/fs"
	"net/http"
	"path"
	"strings"
	"time"
)

// New returns the root handler: API routes plus the SPA in web (may be empty before a web build;
// nil on Vercel, which serves the web app itself).
func New(db *sql.DB, web fs.FS) http.Handler {
	mux := http.NewServeMux()
	(&accounts{db: db, now: time.Now}).routes(mux)
	notFound := func(w http.ResponseWriter, _ *http.Request) { fail(w, http.StatusNotFound, "not_found") }
	mux.HandleFunc("GET /api/", notFound) // not the SPA's index.html
	mux.HandleFunc("POST /api/", notFound)
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
	if web != nil {
		mux.Handle("GET /", spa(web))
	}
	return mux
}

// spa serves files from web and falls back to index.html for client-side routes.
// Missing files with an extension (assets) stay 404.
func spa(web fs.FS) http.Handler {
	files := http.FileServerFS(web)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, err := fs.Stat(web, "index.html"); err != nil {
			http.Error(w, "web app not built", http.StatusServiceUnavailable)
			return
		}
		name := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if name == "" || fileExists(web, name) || path.Ext(name) != "" {
			files.ServeHTTP(w, r)
			return
		}
		http.ServeFileFS(w, r, web, "index.html")
	})
}

func fileExists(fsys fs.FS, name string) bool {
	info, err := fs.Stat(fsys, name)
	return err == nil && !info.IsDir()
}
