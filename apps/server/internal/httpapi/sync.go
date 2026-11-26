package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
)

const (
	maxPush  = 500 // docs per request; the client sends batches
	pullPage = 500
	maxDoc   = 8 << 10
)

// syncKinds are the local tables that sync (see apps/web/src/lib/sync.ts).
var syncKinds = map[string]bool{
	"activity": true, "reviews": true, "cards": true, "unitProgress": true, "itemStats": true,
}

type doc struct {
	Kind string          `json:"kind"`
	ID   string          `json:"id"`
	V    string          `json:"v"`
	Data json.RawMessage `json:"data"`
}

type syncRequest struct {
	Since int64 `json:"since"`
	Docs  []doc `json:"docs"`
}

type syncResponse struct {
	Docs   []doc `json:"docs"`
	Cursor int64 `json:"cursor"`
	More   bool  `json:"more"`
}

// sync stores the pushed docs (a doc only replaces a stored one with a larger v), then returns
// the docs changed after `since`, a page at a time. Merging is the client's job.
func (a *accounts) sync(w http.ResponseWriter, r *http.Request) {
	userID, _, ok := a.current(r)
	if !ok {
		fail(w, http.StatusUnauthorized, "not_logged_in")
		return
	}
	var req syncRequest
	if !readJSON(w, r, 8<<20, &req) {
		return
	}
	if len(req.Docs) > maxPush {
		fail(w, http.StatusBadRequest, "too_many_docs")
		return
	}
	for _, d := range req.Docs {
		if !syncKinds[d.Kind] || d.ID == "" || len(d.ID) > 200 || d.V == "" || len(d.V) > 64 ||
			len(d.Data) > maxDoc || !bytes.HasPrefix(bytes.TrimSpace(d.Data), []byte("{")) {
			fail(w, http.StatusBadRequest, "bad_doc")
			return
		}
	}
	if len(req.Docs) > 0 {
		if err := a.push(r, userID, req.Docs); err != nil {
			internal(w, err)
			return
		}
	}
	rows, err := a.db.QueryContext(r.Context(),
		`SELECT kind, id, v, data, seq FROM sync_docs WHERE user_id = ? AND seq > ?
		 ORDER BY seq LIMIT ?`, userID, req.Since, pullPage+1)
	if err != nil {
		internal(w, err)
		return
	}
	defer rows.Close()
	res := syncResponse{Docs: []doc{}, Cursor: req.Since}
	for rows.Next() {
		var d doc
		var data string
		var seq int64
		if err := rows.Scan(&d.Kind, &d.ID, &d.V, &data, &seq); err != nil {
			internal(w, err)
			return
		}
		if len(res.Docs) == pullPage {
			res.More = true
			break
		}
		d.Data = json.RawMessage(data)
		res.Docs = append(res.Docs, d)
		res.Cursor = seq
	}
	if err := rows.Err(); err != nil {
		internal(w, err)
		return
	}
	writeJSON(w, http.StatusOK, res)
}

// push upserts docs in one transaction, each changed doc getting the user's next seq.
func (a *accounts) push(r *http.Request, userID int64, docs []doc) error {
	tx, err := a.db.BeginTx(r.Context(), nil)
	if err != nil {
		return err
	}
	defer tx.Rollback() //nolint:errcheck // no-op after Commit
	var seq int64
	if err := tx.QueryRowContext(r.Context(),
		`SELECT COALESCE(MAX(seq), 0) FROM sync_docs WHERE user_id = ?`, userID).Scan(&seq); err != nil {
		return err
	}
	for _, d := range docs {
		seq++
		if _, err := tx.ExecContext(r.Context(),
			`INSERT INTO sync_docs (user_id, kind, id, v, data, seq) VALUES (?, ?, ?, ?, ?, ?)
			 ON CONFLICT (user_id, kind, id) DO UPDATE SET v = excluded.v, data = excluded.data,
			 seq = excluded.seq WHERE excluded.v > sync_docs.v`,
			userID, d.Kind, d.ID, d.V, string(d.Data), seq); err != nil {
			return err
		}
	}
	return tx.Commit()
}
