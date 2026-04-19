DROP INDEX IF EXISTS idx_posts_published;

ALTER TABLE posts DROP COLUMN published;
