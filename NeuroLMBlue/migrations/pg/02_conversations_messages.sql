-- Update existing conversations table or create if not exists
DO $$
BEGIN
  -- Add missing columns to existing conversations table
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'topic') THEN
    ALTER TABLE conversations ADD COLUMN topic TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'sub_topic') THEN
    ALTER TABLE conversations ADD COLUMN sub_topic TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'last_message') THEN
    ALTER TABLE conversations ADD COLUMN last_message TEXT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'message_count') THEN
    ALTER TABLE conversations ADD COLUMN message_count INTEGER DEFAULT 0;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'is_active') THEN
    ALTER TABLE conversations ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
  END IF;
END$$;

-- Create messages table compatible with existing conversations.id type
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  message_type TEXT NOT NULL CHECK (message_type IN ('user','assistant','system')),
  content TEXT NOT NULL,
  idempotency_key TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  is_active BOOLEAN DEFAULT TRUE
);

-- FK + indexes for join and fast listing
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'fk_messages_conversation'
  ) THEN
    ALTER TABLE messages 
    ADD CONSTRAINT fk_messages_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_topic ON conversations (topic, sub_topic);

-- Idempotency (scope per-conversation)
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique_idem
  ON messages (conversation_id, idempotency_key) WHERE idempotency_key IS NOT NULL;