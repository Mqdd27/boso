package httpapi

import (
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/Mqdd27/boso/apps/server/internal/db"
)

func newServer(t *testing.T) *httptest.Server {
	t.Helper()
	database, err := db.Open(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { database.Close() })
	srv := httptest.NewServer(New(database, nil))
	t.Cleanup(srv.Close)
	return srv
}

func client(t *testing.T) *http.Client {
	t.Helper()
	jar, _ := cookiejar.New(nil)
	return &http.Client{Jar: jar}
}

func call(t *testing.T, c *http.Client, srv *httptest.Server, method, path, body string) (int, string) {
	t.Helper()
	req, _ := http.NewRequest(method, srv.URL+path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	res, err := c.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	b, _ := io.ReadAll(res.Body)
	return res.StatusCode, string(b)
}

func TestAccountFlow(t *testing.T) {
	srv := newServer(t)
	a, b := client(t), client(t)
	const creds = `{"email":"ana@example.com","password":"hunter22!"}`
	steps := []struct {
		name   string
		c      *http.Client
		method string
		path   string
		body   string
		code   int
		want   string
	}{
		{"not logged in", a, "GET", "/api/me", "", 401, "not_logged_in"},
		{"bad email", a, "POST", "/api/signup", `{"email":"nope","password":"hunter22!"}`, 400, "invalid_email"},
		{"short password", a, "POST", "/api/signup", `{"email":"ana@example.com","password":"short"}`, 400, "weak_password"},
		{"signup", a, "POST", "/api/signup", creds, 201, "ana@example.com"},
		{"logged in after signup", a, "GET", "/api/me", "", 200, "ana@example.com"},
		{"email taken (any case)", b, "POST", "/api/signup", `{"email":"ANA@example.com","password":"hunter22!"}`, 409, "email_taken"},
		{"wrong password", b, "POST", "/api/login", `{"email":"ana@example.com","password":"wrong-one"}`, 401, "wrong_login"},
		{"unknown email", b, "POST", "/api/login", `{"email":"bo@example.com","password":"hunter22!"}`, 401, "wrong_login"},
		{"login", b, "POST", "/api/login", creds, 200, "ana@example.com"},
		{"second device logged in", b, "GET", "/api/me", "", 200, "ana@example.com"},
		{"logout", a, "POST", "/api/logout", "", 204, ""},
		{"logged out", a, "GET", "/api/me", "", 401, "not_logged_in"},
		{"other session still valid", b, "GET", "/api/me", "", 200, "ana@example.com"},
		{"unknown api route", a, "GET", "/api/nope", "", 404, "not_found"},
	}
	for _, s := range steps {
		code, body := call(t, s.c, srv, s.method, s.path, s.body)
		if code != s.code || !strings.Contains(body, s.want) {
			t.Fatalf("%s: got %d %q, want %d containing %q", s.name, code, body, s.code, s.want)
		}
	}
}

func TestFormPostRejected(t *testing.T) {
	srv := newServer(t)
	res, err := http.Post(srv.URL+"/api/login", "application/x-www-form-urlencoded",
		strings.NewReader("email=a&password=b"))
	if err != nil {
		t.Fatal(err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusUnsupportedMediaType {
		t.Fatalf("code = %d, want 415", res.StatusCode)
	}
}

func TestSessionCookie(t *testing.T) {
	srv := newServer(t)
	c := client(t)
	call(t, c, srv, "POST", "/api/signup", `{"email":"x@example.com","password":"hunter22!"}`)
	req, _ := http.NewRequest("POST", srv.URL+"/api/login",
		strings.NewReader(`{"email":"x@example.com","password":"hunter22!"}`))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Forwarded-Proto", "https")
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	res.Body.Close()
	ck := res.Cookies()[0]
	if !ck.HttpOnly || !ck.Secure || ck.SameSite != http.SameSiteLaxMode ||
		ck.MaxAge != sessionDays*24*60*60 {
		t.Fatalf("cookie = %+v", ck)
	}
}

func TestExpiredSession(t *testing.T) {
	database, err := db.Open(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer database.Close()
	now := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	a := &accounts{db: database, now: func() time.Time { return now }}
	mux := http.NewServeMux()
	a.routes(mux)
	rec := httptest.NewRecorder()
	req := httptest.NewRequest("POST", "/api/signup",
		strings.NewReader(`{"email":"x@example.com","password":"hunter22!"}`))
	req.Header.Set("Content-Type", "application/json")
	mux.ServeHTTP(rec, req)
	ck := rec.Result().Cookies()[0]
	for _, tt := range []struct {
		after time.Duration
		code  int
	}{{29 * 24 * time.Hour, 200}, {31 * 24 * time.Hour, 401}} {
		now = time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC).Add(tt.after)
		rec := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/api/me", nil)
		req.AddCookie(ck)
		mux.ServeHTTP(rec, req)
		if rec.Code != tt.code {
			t.Errorf("after %v: code %d, want %d", tt.after, rec.Code, tt.code)
		}
	}
}
