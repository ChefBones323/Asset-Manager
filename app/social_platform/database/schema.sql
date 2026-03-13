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

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(event_id),
    domain VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    actor_id UUID NOT NULL,
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),
    summary TEXT,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_id ON audit_logs (event_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_domain ON audit_logs (domain);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_id ON audit_logs (resource_id);

CREATE OR REPLACE RULE prevent_update_audit_logs AS
    ON UPDATE TO audit_logs DO INSTEAD NOTHING;

CREATE OR REPLACE RULE prevent_delete_audit_logs AS
    ON DELETE TO audit_logs DO INSTEAD NOTHING;

CREATE TABLE IF NOT EXISTS agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_category ON agent_memory (category);
CREATE INDEX IF NOT EXISTS idx_agent_memory_key ON agent_memory (key);
