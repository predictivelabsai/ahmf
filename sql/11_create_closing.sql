-- Deal Closing & Data Room
CREATE TABLE IF NOT EXISTS ahmf.closing_checklists (
    checklist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE CASCADE,
    title VARCHAR(500) DEFAULT 'Closing Checklist',
    status VARCHAR(50) DEFAULT 'in_progress',
    created_by UUID REFERENCES ahmf.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ahmf.checklist_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id UUID REFERENCES ahmf.closing_checklists(checklist_id) ON DELETE CASCADE,
    category VARCHAR(100),
    description TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    assigned_to VARCHAR(255),
    due_date DATE,
    completed_at TIMESTAMPTZ,
    sort_order INTEGER DEFAULT 0
);
