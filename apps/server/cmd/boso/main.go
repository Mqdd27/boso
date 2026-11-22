// Command boso runs the boso server: API + embedded web app.
package main

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	boso "github.com/Mqdd27/boso/apps/server"
	"github.com/Mqdd27/boso/apps/server/internal/config"
	"github.com/Mqdd27/boso/apps/server/internal/db"
	"github.com/Mqdd27/boso/apps/server/internal/httpapi"
)

func main() {
	if err := run(); err != nil {
		slog.Error("boso", "err", err)
		os.Exit(1)
	}
}

func run() error {
	cfg := config.FromEnv(os.Getenv)

	database, err := db.Open(cfg.DataDir)
	if err != nil {
		return err
	}
	defer database.Close()

	web, err := fs.Sub(boso.Web, "web/dist")
	if err != nil {
		return fmt.Errorf("web fs: %w", err)
	}

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           httpapi.New(web),
		ReadHeaderTimeout: 10 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdown)
	}()

	slog.Info("listening", "addr", cfg.Addr, "data_dir", cfg.DataDir)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("listen: %w", err)
	}
	return nil
}
