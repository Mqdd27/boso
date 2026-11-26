package httpapi

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"
)

func TestRoutes(t *testing.T) {
	web := fstest.MapFS{
		"index.html":  {Data: []byte("<html>index</html>")},
		"_app/app.js": {Data: []byte("console.log(1)")},
	}
	tests := []struct {
		name     string
		web      fstest.MapFS
		path     string
		wantCode int
		wantBody string
	}{
		{"healthz", web, "/healthz", 200, `{"status":"ok"}`},
		{"index", web, "/", 200, "index"},
		{"asset", web, "/_app/app.js", 200, "console.log"},
		{"spa fallback", web, "/learn/ko-en", 200, "index"},
		{"missing asset", web, "/_app/missing.js", 404, ""},
		{"not built", fstest.MapFS{}, "/", 503, "not built"},
		{"healthz without web", fstest.MapFS{}, "/healthz", 200, `"ok"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := httptest.NewRecorder()
			New(nil, tt.web).ServeHTTP(rec, httptest.NewRequest(http.MethodGet, tt.path, nil))
			if rec.Code != tt.wantCode {
				t.Fatalf("code = %d, want %d", rec.Code, tt.wantCode)
			}
			if !strings.Contains(rec.Body.String(), tt.wantBody) {
				t.Fatalf("body = %q, want it to contain %q", rec.Body.String(), tt.wantBody)
			}
		})
	}
}
