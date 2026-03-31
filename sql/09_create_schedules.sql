-- Production Scheduling
CREATE TABLE IF NOT EXISTS ahmf.schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    project_params JSONB DEFAULT '{}',
    total_days INTEGER,
    start_date DATE,
    end_date DATE,
    analysis_text TEXT,
    created_by UUID REFERENCES ahmf.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ahmf.schedule_days (
    day_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES ahmf.schedules(schedule_id) ON DELETE CASCADE,
    day_number INTEGER,
    shoot_date DATE,
    location VARCHAR(500),
    scenes TEXT,
    call_time VARCHAR(20),
    wrap_time VARCHAR(20),
    notes TEXT,
    sort_order INTEGER DEFAULT 0
);
