ALTER TABLE posts ADD COLUMN published INTEGER NOT NULL DEFAULT 0;

CREATE INDEX idx_posts_published ON posts(published);
