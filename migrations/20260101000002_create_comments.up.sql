CREATE TABLE comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author     TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_comments_post_id ON comments(post_id);
