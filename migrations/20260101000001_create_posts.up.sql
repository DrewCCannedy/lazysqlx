CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    author     TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_posts_created_at ON posts(created_at);
