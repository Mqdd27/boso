package httpapi

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func pull(t *testing.T, body string) syncResponse {
	t.Helper()
	var r syncResponse
	if err := json.Unmarshal([]byte(body), &r); err != nil {
		t.Fatalf("%v: %s", err, body)
	}
	return r
}

func TestSync(t *testing.T) {
	srv := newServer(t)
	phone, laptop, other := client(t), client(t), client(t)
	const ana = `{"email":"ana@example.com","password":"hunter22!"}`
	call(t, phone, srv, "POST", "/api/signup", ana)
	call(t, laptop, srv, "POST", "/api/login", ana)
	call(t, other, srv, "POST", "/api/signup", `{"email":"bo@example.com","password":"hunter22!"}`)

	card := func(v, due string) string {
		return fmt.Sprintf(`{"kind":"cards","id":"ko.w.ne","v":%q,"data":{"due":%q}}`, v, due)
	}
	code, body := call(t, phone, srv, "POST", "/api/sync",
		`{"since":0,"docs":[`+card("2026-11-02", "new")+`,{"kind":"activity","id":"a1","v":"x","data":{}}]}`)
	first := pull(t, body)
	if code != 200 || len(first.Docs) != 2 || first.Cursor != 2 {
		t.Fatalf("push: %d %s", code, body)
	}

	// An older write (a device that was offline) doesn't replace the newer card.
	_, body = call(t, laptop, srv, "POST", "/api/sync", `{"since":2,"docs":[`+card("2026-11-01", "old")+`]}`)
	if r := pull(t, body); len(r.Docs) != 0 || r.Cursor != 2 {
		t.Fatalf("older write changed something: %s", body)
	}
	// A newer one does, and the other device pulls it.
	call(t, laptop, srv, "POST", "/api/sync", `{"since":2,"docs":[`+card("2026-11-03", "newer")+`]}`)
	_, body = call(t, phone, srv, "POST", "/api/sync", `{"since":2,"docs":[]}`)
	if r := pull(t, body); len(r.Docs) != 1 || !strings.Contains(string(r.Docs[0].Data), "newer") {
		t.Fatalf("pull: %s", body)
	}
	// Other users see nothing of it.
	_, body = call(t, other, srv, "POST", "/api/sync", `{"since":0}`)
	if r := pull(t, body); len(r.Docs) != 0 {
		t.Fatalf("leak: %s", body)
	}

	for _, tc := range []struct{ name, body string }{
		{"unknown kind", `{"docs":[{"kind":"users","id":"1","v":"1","data":{}}]}`},
		{"data not an object", `{"docs":[{"kind":"cards","id":"1","v":"1","data":"x"}]}`},
		{"no v", `{"docs":[{"kind":"cards","id":"1","v":"","data":{}}]}`},
	} {
		if code, body := call(t, phone, srv, "POST", "/api/sync", tc.body); code != 400 {
			t.Errorf("%s: %d %s", tc.name, code, body)
		}
	}
	if code, _ := call(t, client(t), srv, "POST", "/api/sync", `{}`); code != 401 {
		t.Errorf("logged out: %d", code)
	}
}

func TestSyncPages(t *testing.T) {
	srv := newServer(t)
	c := client(t)
	call(t, c, srv, "POST", "/api/signup", `{"email":"ana@example.com","password":"hunter22!"}`)
	for _, batch := range []string{"a", "b"} {
		docs := make([]string, maxPush)
		for i := range docs {
			docs[i] = fmt.Sprintf(`{"kind":"reviews","id":"%s%d","v":"1","data":{}}`, batch, i)
		}
		if code, body := call(t, c, srv, "POST", "/api/sync",
			`{"docs":[`+strings.Join(docs, ",")+`]}`); code != 200 {
			t.Fatalf("push %s: %d %.200s", batch, code, body)
		}
	}
	_, body := call(t, c, srv, "POST", "/api/sync", `{"since":0}`)
	r := pull(t, body)
	if len(r.Docs) != pullPage || !r.More {
		t.Fatalf("first page: %d more=%v", len(r.Docs), r.More)
	}
	_, body = call(t, c, srv, "POST", "/api/sync", fmt.Sprintf(`{"since":%d}`, r.Cursor))
	if r := pull(t, body); len(r.Docs) != 500 || r.More {
		t.Fatalf("second page: %d more=%v", len(r.Docs), r.More)
	}
}
