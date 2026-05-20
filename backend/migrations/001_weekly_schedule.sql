CREATE TABLE IF NOT EXISTS user_schedule (
    user_id            TEXT        PRIMARY KEY,
    days               JSONB       NOT NULL DEFAULT '{}',
    fixed_commitments  JSONB       NOT NULL DEFAULT '[]',
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
