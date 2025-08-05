-- These tables are assumed to exist from your Secrets Vault implementation
-- Enforce RLS; the app must SET app.current_user per request/session
ALTER TABLE IF EXISTS user_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_secret_salts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS secret_access_log ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public'
      AND tablename = 'user_secrets' AND policyname = 'user_secrets_isolation'
  ) THEN
    CREATE POLICY user_secrets_isolation ON user_secrets
      FOR SELECT USING (user_id = current_setting('app.current_user', true));
  END IF;
END$$;