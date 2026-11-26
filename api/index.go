// Vercel Go function: every /api/* request is rewritten here (vercel.json) and served by the
// boso API. The code lives in apps/server; this file only hands the request over.
package handler

import (
	"net/http"

	"github.com/Mqdd27/boso/apps/server/vercel"
)

// Handler is the function's entry point.
func Handler(w http.ResponseWriter, r *http.Request) {
	vercel.Handler(w, r)
}
