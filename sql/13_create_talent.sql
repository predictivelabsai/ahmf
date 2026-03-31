-- Talent Intelligence
CREATE TABLE IF NOT EXISTS ahmf.talent_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    project_params JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    package_sims JSONB DEFAULT '[]',
    analysis_text TEXT,
    created_by UUID REFERENCES ahmf.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
