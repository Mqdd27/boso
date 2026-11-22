// Package config reads server settings from environment variables.
package config

// Config is the server configuration.
type Config struct {
	Addr    string // BOSO_ADDR, listen address
	DataDir string // BOSO_DATA_DIR, holds boso.db and courses/
}

// FromEnv builds a Config from getenv (usually os.Getenv), applying defaults.
func FromEnv(getenv func(string) string) Config {
	return Config{
		Addr:    or(getenv("BOSO_ADDR"), ":8080"),
		DataDir: or(getenv("BOSO_DATA_DIR"), "/data"),
	}
}

func or(v, def string) string {
	if v == "" {
		return def
	}
	return v
}
