-- Basic Chatbot Schema for Supabase PostgreSQL
-- Tables: users, threads, messages
-- Idempotent: safe to run multiple times

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- USERS
-- Supports signup/signin via email + password_hash
-- Signup: insert email + crypt(password, gen_salt('bf'))
-- Signin: compare password with crypt(input_password, password_hash)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  full_name VARCHAR(120),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- -----------------------------------------------------------------------------
-- THREADS
-- Each thread belongs to exactly one user
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS threads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);

-- -----------------------------------------------------------------------------
-- MESSAGES
-- Each message belongs to one thread and one user
-- role is typically: user | assistant
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- -----------------------------------------------------------------------------
-- Trigger for updated_at
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_threads_updated_at ON threads;
CREATE TRIGGER trg_threads_updated_at
BEFORE UPDATE ON threads
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- -----------------------------------------------------------------------------
-- Optional helper functions for signup/signin
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION signup_user(p_email TEXT, p_password TEXT, p_full_name TEXT DEFAULT NULL)
RETURNS UUID AS $$
DECLARE
  v_user_id UUID;
BEGIN
  INSERT INTO users (email, password_hash, full_name)
  VALUES (LOWER(TRIM(p_email)), crypt(p_password, gen_salt('bf')), p_full_name)
  RETURNING id INTO v_user_id;

  RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION signin_user(p_email TEXT, p_password TEXT)
RETURNS UUID AS $$
DECLARE
  v_user_id UUID;
BEGIN
  SELECT id
  INTO v_user_id
  FROM users
  WHERE email = LOWER(TRIM(p_email))
    AND password_hash = crypt(p_password, password_hash)
    AND is_active = TRUE;

  IF v_user_id IS NOT NULL THEN
    UPDATE users
    SET last_login_at = CURRENT_TIMESTAMP
    WHERE id = v_user_id;
  END IF;

  RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;
