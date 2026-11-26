-- +goose Up
-- Synced progress, one row per document (an activity event, a review, an FSRS card, unit
-- progress, item stats). The server doesn't interpret `data`; `v` decides which write wins
-- (the larger one, compared as text: ISO timestamps). `seq` orders changes per user, so a
-- device pulls only what changed since its cursor.
CREATE TABLE sync_docs (
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind    TEXT NOT NULL,
    id      TEXT NOT NULL,
    v       TEXT NOT NULL,
    data    TEXT NOT NULL,
    seq     INTEGER NOT NULL,
    PRIMARY KEY (user_id, kind, id)
) STRICT;
CREATE INDEX sync_docs_seq ON sync_docs (user_id, seq);

-- +goose Down
DROP TABLE sync_docs;
