-- Adjust dimension for the embedding model you use (1536 as a default)
CREATE TABLE IF NOT EXISTS messages_embeddings (
  message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_embeddings_ivfflat
  ON messages_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);