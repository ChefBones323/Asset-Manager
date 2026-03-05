CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    actor_id UUID NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    manifest_id UUID,
    execution_id UUID,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
    signature TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_domain ON events (domain);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_actor_id ON events (actor_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events ("timestamp");

CREATE OR REPLACE RULE prevent_update_events AS
    ON UPDATE TO events DO INSTEAD NOTHING;

CREATE OR REPLACE RULE prevent_delete_events AS
    ON DELETE TO events DO INSTEAD NOTHING;
