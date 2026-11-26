package httpapi

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log/slog"
	"mime"
	"net/http"
	"net/mail"
	"strings"
	"time"

	"github.com/Mqdd27/boso/apps/server/internal/auth"
)

const (
	cookieName  = "boso_session"
	sessionDays = 30
	minPassword = 8
	maxPassword = 256
)

// dummyHash is verified against when the email is unknown, so a login takes as long either way.
var dummyHash, _ = auth.Hash("not a real password")

type accounts struct {
	db  *sql.DB
	now func() time.Time
}

type credentials struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type user struct {
	Email string `json:"email"`
}

func (a *accounts) routes(mux *http.ServeMux) {
	mux.HandleFunc("POST /api/signup", a.signup)
	mux.HandleFunc("POST /api/login", a.login)
	mux.HandleFunc("POST /api/logout", a.logout)
	mux.HandleFunc("GET /api/me", a.me)
}

func (a *accounts) signup(w http.ResponseWriter, r *http.Request) {
	c, ok := readCredentials(w, r)
	if !ok {
		return
	}
	addr, err := mail.ParseAddress(c.Email)
	if err != nil || addr.Address != c.Email || len(c.Email) > 254 {
		fail(w, http.StatusBadRequest, "invalid_email")
		return
	}
	if n := len([]rune(c.Password)); n < minPassword || len(c.Password) > maxPassword {
		fail(w, http.StatusBadRequest, "weak_password")
		return
	}
	hash, err := auth.Hash(c.Password)
	if err != nil {
		internal(w, err)
		return
	}
	res, err := a.db.ExecContext(r.Context(),
		`INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)`,
		c.Email, hash, a.now().UTC().Format(time.RFC3339))
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			fail(w, http.StatusConflict, "email_taken")
			return
		}
		internal(w, err)
		return
	}
	id, err := res.LastInsertId()
	if err != nil {
		internal(w, err)
		return
	}
	a.startSession(w, r, id, c.Email, http.StatusCreated)
}

func (a *accounts) login(w http.ResponseWriter, r *http.Request) {
	c, ok := readCredentials(w, r)
	if !ok {
		return
	}
	var id int64
	var email, hash string
	err := a.db.QueryRowContext(r.Context(),
		`SELECT id, email, password_hash FROM users WHERE email = ?`, c.Email).Scan(&id, &email, &hash)
	if errors.Is(err, sql.ErrNoRows) {
		hash = dummyHash
	} else if err != nil {
		internal(w, err)
		return
	}
	match, err := auth.Verify(c.Password, hash)
	if err != nil {
		internal(w, err)
		return
	}
	if !match || id == 0 {
		fail(w, http.StatusUnauthorized, "wrong_login")
		return
	}
	a.startSession(w, r, id, email, http.StatusOK)
}

func (a *accounts) logout(w http.ResponseWriter, r *http.Request) {
	if c, err := r.Cookie(cookieName); err == nil {
		if _, err := a.db.ExecContext(r.Context(),
			`DELETE FROM sessions WHERE token_hash = ?`, auth.TokenHash(c.Value)); err != nil {
			internal(w, err)
			return
		}
	}
	http.SetCookie(w, cookie(r, "", -1))
	w.WriteHeader(http.StatusNoContent)
}

func (a *accounts) me(w http.ResponseWriter, r *http.Request) {
	_, email, ok := a.current(r)
	if !ok {
		fail(w, http.StatusUnauthorized, "not_logged_in")
		return
	}
	writeJSON(w, http.StatusOK, user{email})
}

// current returns the logged-in user of a request (a valid, unexpired session cookie).
func (a *accounts) current(r *http.Request) (id int64, email string, ok bool) {
	c, err := r.Cookie(cookieName)
	if err != nil {
		return 0, "", false
	}
	err = a.db.QueryRowContext(r.Context(),
		`SELECT u.id, u.email FROM sessions s JOIN users u ON u.id = s.user_id
		 WHERE s.token_hash = ? AND s.expires_at > ?`,
		auth.TokenHash(c.Value), a.now().UTC().Format(time.RFC3339)).Scan(&id, &email)
	if err != nil {
		if !errors.Is(err, sql.ErrNoRows) {
			slog.Error("session lookup", "err", err)
		}
		return 0, "", false
	}
	return id, email, true
}

func (a *accounts) startSession(w http.ResponseWriter, r *http.Request, id int64, email string, code int) {
	token, hash, err := auth.NewToken()
	if err != nil {
		internal(w, err)
		return
	}
	expires := a.now().UTC().Add(sessionDays * 24 * time.Hour)
	if _, err := a.db.ExecContext(r.Context(),
		`INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)`,
		hash, id, expires.Format(time.RFC3339)); err != nil {
		internal(w, err)
		return
	}
	http.SetCookie(w, cookie(r, token, sessionDays*24*60*60))
	writeJSON(w, code, user{email})
}

// cookie is HttpOnly and SameSite=Lax; Secure behind HTTPS (directly or via a proxy like Vercel).
func cookie(r *http.Request, value string, maxAge int) *http.Cookie {
	return &http.Cookie{
		Name:     cookieName,
		Value:    value,
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: true,
		Secure:   r.TLS != nil || r.Header.Get("X-Forwarded-Proto") == "https",
		SameSite: http.SameSiteLaxMode,
	}
}

// readCredentials only accepts a JSON body: a cross-site form can't send one without a CORS
// preflight, which this API never allows (CSRF protection together with SameSite=Lax).
func readCredentials(w http.ResponseWriter, r *http.Request) (credentials, bool) {
	var c credentials
	if t, _, _ := mime.ParseMediaType(r.Header.Get("Content-Type")); t != "application/json" {
		fail(w, http.StatusUnsupportedMediaType, "json_only")
		return c, false
	}
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&c); err != nil {
		fail(w, http.StatusBadRequest, "bad_json")
		return c, false
	}
	c.Email = strings.TrimSpace(c.Email)
	return c, true
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func fail(w http.ResponseWriter, code int, reason string) {
	writeJSON(w, code, map[string]string{"error": reason})
}

func internal(w http.ResponseWriter, err error) {
	slog.Error("api", "err", err)
	fail(w, http.StatusInternalServerError, "internal")
}
