-- Add Postiz tracking fields to scheduled_posts
-- Run these commands in your SQLite database (e.g. using DB Browser for SQLite or sqlite3 CLI)

ALTER TABLE scheduled_posts ADD COLUMN postiz_post_id VARCHAR(255);
ALTER TABLE scheduled_posts ADD COLUMN postiz_media_id VARCHAR(255);
ALTER TABLE scheduled_posts ADD COLUMN platforms TEXT;
ALTER TABLE scheduled_posts ADD COLUMN retry_count INTEGER DEFAULT 0;

-- Create Postiz Integrations table
CREATE TABLE IF NOT EXISTS postiz_integrations (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
