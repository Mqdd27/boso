package auth

import "testing"

func TestHashVerify(t *testing.T) {
	h, err := Hash("correct horse")
	if err != nil {
		t.Fatal(err)
	}
	h2, _ := Hash("correct horse")
	if h == h2 {
		t.Fatal("same hash twice: salt not random")
	}
	tests := []struct {
		password string
		want     bool
	}{
		{"correct horse", true},
		{"correct horse ", false},
		{"", false},
	}
	for _, tt := range tests {
		ok, err := Verify(tt.password, h)
		if err != nil || ok != tt.want {
			t.Errorf("Verify(%q) = %v, %v; want %v", tt.password, ok, err, tt.want)
		}
	}
	if _, err := Verify("x", "$2a$10$bcrypt"); err == nil {
		t.Error("non-argon2id hash accepted")
	}
}

func TestToken(t *testing.T) {
	tok, hash, err := NewToken()
	if err != nil || len(tok) < 40 || TokenHash(tok) != hash || hash == tok {
		t.Fatalf("NewToken = %q, %q, %v", tok, hash, err)
	}
}
