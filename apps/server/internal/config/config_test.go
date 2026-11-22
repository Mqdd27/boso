package config

import "testing"

func TestFromEnv(t *testing.T) {
	tests := []struct {
		name string
		env  map[string]string
		want Config
	}{
		{"defaults", nil, Config{Addr: ":8080", DataDir: "/data"}},
		{"overrides", map[string]string{"BOSO_ADDR": "127.0.0.1:9000", "BOSO_DATA_DIR": "/tmp/boso"},
			Config{Addr: "127.0.0.1:9000", DataDir: "/tmp/boso"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := FromEnv(func(k string) string { return tt.env[k] })
			if got != tt.want {
				t.Fatalf("got %+v, want %+v", got, tt.want)
			}
		})
	}
}
