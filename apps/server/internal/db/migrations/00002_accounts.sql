-- +goose Up
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
) STRICT;

-- Only a hash of the session token is stored: a leaked database can't be used to log in.
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
) STRICT;
CREATE INDEX sessions_user ON sessions (user_id);

-- +goose Down
DROP TABLE sessions;
DROP TABLE users;
