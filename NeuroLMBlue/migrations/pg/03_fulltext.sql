ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS ts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages USING GIN (ts);