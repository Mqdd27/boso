// Package boso holds the embedded web app. The SvelteKit build writes into web/dist.
package boso

import "embed"

// Web contains web/dist (the built SPA) once `npm run build` has run.
// web/.gitkeep keeps the embed valid before the first web build.
//
//go:embed all:web
var Web embed.FS
