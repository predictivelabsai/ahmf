-- Smart Budgeting
CREATE TABLE IF NOT EXISTS ahmf.budgets (
    budget_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    project_params JSONB DEFAULT '{}',
    scenario VARCHAR(20) DEFAULT 'mid',
    total_amount NUMERIC(15,2),
    currency VARCHAR(10) DEFAULT 'USD',
    breakdown JSONB DEFAULT '{}',
    analysis_text TEXT,
    created_by UUID REFERENCES ahmf.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ahmf.budget_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id UUID REFERENCES ahmf.budgets(budget_id) ON DELETE CASCADE,
    category VARCHAR(100),
    subcategory VARCHAR(200),
    description TEXT,
    amount NUMERIC(15,2),
    sort_order INTEGER DEFAULT 0
);
