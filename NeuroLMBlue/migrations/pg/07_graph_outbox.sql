-- For resilient Neo4j sync (outbox pattern)
CREATE TABLE IF NOT EXISTS graph_outbox (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL, -- e.g., 'conversation_upsert','message_upsert','feedback'
  entity_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, done, deadletter
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_graph_outbox_status_created ON graph_outbox (status, created_at);