-- Production Risk Scoring
CREATE TABLE IF NOT EXISTS ahmf.risk_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    project_details JSONB DEFAULT '{}',
    scores JSONB DEFAULT '{}',
    overall_score NUMERIC(5,2),
    risk_tier VARCHAR(20),
    mitigations JSONB DEFAULT '[]',
    analysis_text TEXT,
    created_by UUID REFERENCES ahmf.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
