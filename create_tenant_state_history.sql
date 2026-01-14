CREATE TABLE IF NOT EXISTS tenant_state_history (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    previous_state VARCHAR(20),
    new_state VARCHAR(20) NOT NULL,
    previous_replicas INTEGER,
    new_replicas INTEGER NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255),
    reason TEXT,
    CONSTRAINT check_valid_state CHECK (new_state IN ('running', 'stopped', 'scaling', 'unknown'))
);

CREATE INDEX IF NOT EXISTS idx_tenant_state_history_tenant_id ON tenant_state_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_state_history_new_state ON tenant_state_history(new_state);
CREATE INDEX IF NOT EXISTS idx_tenant_state_history_changed_at ON tenant_state_history(changed_at);

INSERT INTO alembic_version (version_num) VALUES ('004_tenant_state_history') ON CONFLICT DO NOTHING;
