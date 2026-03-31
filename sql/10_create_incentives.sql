-- Soft Funding / Incentive Programs
CREATE TABLE IF NOT EXISTS ahmf.incentive_programs (
    program_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL,
    country VARCHAR(100),
    region VARCHAR(200),
    incentive_type VARCHAR(50),
    rebate_percent NUMERIC(5,2),
    max_rebate NUMERIC(15,2),
    min_spend NUMERIC(15,2),
    currency VARCHAR(10) DEFAULT 'USD',
    eligibility TEXT,
    application_url TEXT,
    avg_processing_days INTEGER,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ahmf.deal_incentives (
    deal_id UUID REFERENCES ahmf.deals(deal_id) ON DELETE CASCADE,
    program_id UUID REFERENCES ahmf.incentive_programs(program_id) ON DELETE CASCADE,
    estimated_rebate NUMERIC(15,2),
    status VARCHAR(50) DEFAULT 'identified',
    notes TEXT,
    PRIMARY KEY (deal_id, program_id)
);

-- Seed data: major global film incentive programs
INSERT INTO ahmf.incentive_programs (name, country, region, incentive_type, rebate_percent, min_spend, avg_processing_days, eligibility, notes) VALUES
('Georgia Tax Credit', 'USA', 'Georgia', 'tax_credit', 30.00, 500000, 120, 'Must spend min $500K in GA. 10% uplift for GA logo.', 'One of the most generous US state incentives.'),
('New Mexico Tax Credit', 'USA', 'New Mexico', 'tax_credit', 25.00, 0, 90, 'Direct spend in NM on resident/non-resident crew.', 'Additional 5% for TV pilots/series.'),
('Louisiana Tax Credit', 'USA', 'Louisiana', 'tax_credit', 25.00, 300000, 150, 'Min spend $300K. Additional 5% for LA resident labor.', 'Transferable credits.'),
('New York Tax Credit', 'USA', 'New York', 'tax_credit', 25.00, 0, 180, 'Qualified production spend in NY. 10% additional upstate.', 'Competitive application process.'),
('UK Tax Relief (HETV/Film)', 'UK', 'United Kingdom', 'tax_relief', 25.50, 0, 90, 'BFI cultural test or official co-production. Min 10% UK spend.', 'Applies to qualifying core expenditure.'),
('Canada Federal (CPTC)', 'Canada', 'Federal', 'tax_credit', 25.00, 0, 120, 'Canadian-controlled production. Points system for Canadian content.', 'Stackable with provincial credits.'),
('Ontario (OFTTC)', 'Canada', 'Ontario', 'tax_credit', 35.00, 0, 90, 'Ontario-based Canadian corp. Qualifying labor expenditures.', 'Stacks with federal CPTC.'),
('British Columbia (FIBC)', 'Canada', 'British Columbia', 'tax_credit', 28.00, 0, 90, 'BC-based production. Qualifying BC labor.', 'Additional regional + training credits.'),
('Australia (PDV Offset)', 'Australia', 'Federal', 'tax_offset', 30.00, 500000, 120, 'Post/VFX/digital spend in AU. Min AUD $500K QAPE.', '16.5% Location Offset also available.'),
('Hungary Cash Rebate', 'Hungary', 'Hungary', 'cash_rebate', 30.00, 0, 60, 'Qualifying spend in Hungary. Cultural test.', 'Fast turnaround. No cap.'),
('Czech Republic Incentive', 'Czech Republic', 'Czech Republic', 'cash_rebate', 20.00, 0, 90, 'Qualifying Czech spend. Cultural contribution test.', 'Additional 10% for Czech cast/crew.'),
('France Tax Rebate (TRIP)', 'France', 'France', 'tax_rebate', 30.00, 250000, 120, 'French-approved VFX/animation spend. Cultural criteria.', 'Up to 30% on eligible spend.'),
('Germany (DFFF/GMPF)', 'Germany', 'Germany', 'grant', 20.00, 1000000, 90, 'German theatrical release commitment. Cultural test. Min EUR 1M German spend.', 'Non-recoupable grant.'),
('Ireland Section 481', 'Ireland', 'Ireland', 'tax_credit', 32.00, 250000, 60, 'Irish-based production company. Min EUR 250K eligible spend.', 'One of the highest in Europe.'),
('South Korea Rebate', 'South Korea', 'South Korea', 'cash_rebate', 25.00, 0, 120, 'Foreign production shooting in Korea. Cultural contribution.', 'Growing incentive program.'),
('Colombia Cash Rebate', 'Colombia', 'Colombia', 'cash_rebate', 40.00, 0, 90, 'Filming services or post-production in Colombia.', 'One of the highest global rebates. Capped annually.')
ON CONFLICT DO NOTHING;
