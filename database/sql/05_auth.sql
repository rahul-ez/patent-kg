-- Additive authentication migration. Existing accounts and ownerless cases stay intact.
-- password_hash is added idempotently by backend/scripts/database/migrate_auth.py.
CREATE TABLE IF NOT EXISTS auth_sessions (
  token_hash CHAR(64) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES app_users(user_id) ON DELETE CASCADE,
  INDEX ix_session_user (user_id),
  INDEX ix_session_expiry (expires_at)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS auth_rate_limits (
  bucket_key CHAR(64) PRIMARY KEY,
  attempts INT NOT NULL,
  window_started DATETIME NOT NULL,
  INDEX ix_auth_window (window_started)
) ENGINE=InnoDB;
