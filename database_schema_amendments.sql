-- LeaseAI Amendment Resolution Schema
-- Supports the Amendment Resolution Graph™ feature

-- ============================================================================
-- AMENDMENTS TABLE
-- Stores amendment documents and their metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Link to base lease
    lease_id UUID NOT NULL REFERENCES leases(id) ON DELETE CASCADE,
    
    -- Amendment metadata
    amendment_number INTEGER NOT NULL,  -- 1st amendment, 2nd amendment, etc.
    amendment_date DATE NOT NULL,       -- Date amendment was executed
    effective_date DATE,                -- When amendment takes effect (may differ from execution)
    
    -- Document info
    filename TEXT NOT NULL,
    file_size INTEGER,
    page_count INTEGER,
    
    -- Status tracking
    status TEXT DEFAULT 'PROCESSING',  -- PROCESSING, READY FOR REVIEW, APPROVED, FLAGGED
    
    -- Full extracted data (JSON)
    extracted_data JSONB,
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID,  -- User who uploaded
    
    -- Constraints
    UNIQUE(lease_id, amendment_number)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_amendments_lease_id ON amendments(lease_id);
CREATE INDEX IF NOT EXISTS idx_amendments_date ON amendments(amendment_date DESC);
CREATE INDEX IF NOT EXISTS idx_amendments_status ON amendments(status);


-- ============================================================================
-- AMENDMENT_CLAUSES TABLE
-- Tracks which specific clauses each amendment modifies
-- This is the core of the Amendment Resolution Graph™
-- ============================================================================
CREATE TABLE IF NOT EXISTS amendment_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Link to amendment
    amendment_id UUID NOT NULL REFERENCES amendments(id) ON DELETE CASCADE,
    
    -- Clause identification
    clause_type TEXT NOT NULL,  -- e.g., "Base Rent", "Renewal Options", "Parking"
    clause_section TEXT,        -- e.g., "Section 4.1", "Article 3"
    
    -- What this amendment does to the clause
    modification_type TEXT NOT NULL,  -- MODIFIES, SUPERSEDES, ADDS, DELETES, CONDITIONALLY_MODIFIES
    
    -- The actual change
    original_value TEXT,        -- Value before amendment
    new_value TEXT NOT NULL,    -- Value after amendment
    
    -- Conditional logic (if applicable)
    condition TEXT,             -- e.g., "If tenant exercises renewal option"
    condition_met BOOLEAN,      -- null = unknown, true = condition met, false = not met
    
    -- Effective date for this specific clause change
    effective_date DATE,
    expiration_date DATE,       -- null = permanent change
    
    -- Source text
    source_text TEXT,           -- Exact text from amendment document
    
    -- Confidence & review
    confidence TEXT,            -- HIGH, MEDIUM, LOW
    reviewed BOOLEAN DEFAULT FALSE,
    reviewer_notes TEXT,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for Amendment Resolution Graph queries
CREATE INDEX IF NOT EXISTS idx_amendment_clauses_amendment_id ON amendment_clauses(amendment_id);
CREATE INDEX IF NOT EXISTS idx_amendment_clauses_clause_type ON amendment_clauses(clause_type);
CREATE INDEX IF NOT EXISTS idx_amendment_clauses_effective_date ON amendment_clauses(effective_date);


-- ============================================================================
-- LEASE_CLAUSE_HISTORY TABLE
-- Materialized view of clause evolution over time
-- Powers the "controlling version at any date" query
-- ============================================================================
CREATE TABLE IF NOT EXISTS lease_clause_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What lease and clause
    lease_id UUID NOT NULL REFERENCES leases(id) ON DELETE CASCADE,
    clause_type TEXT NOT NULL,
    
    -- Version chain
    version_number INTEGER NOT NULL,  -- 0 = original lease, 1+ = amendments
    source_document_type TEXT NOT NULL,  -- BASE_LEASE, AMENDMENT
    source_document_id UUID NOT NULL,    -- lease.id or amendment.id
    
    -- The value at this version
    clause_value TEXT NOT NULL,
    
    -- When this version is valid
    effective_from DATE NOT NULL,
    effective_to DATE,  -- null = still current
    
    -- Metadata
    is_current BOOLEAN DEFAULT FALSE,
    modification_type TEXT,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(lease_id, clause_type, version_number)
);

-- Indexes for time-based queries
CREATE INDEX IF NOT EXISTS idx_lease_clause_history_lease_id ON lease_clause_history(lease_id);
CREATE INDEX IF NOT EXISTS idx_lease_clause_history_clause_type ON lease_clause_history(clause_type);
CREATE INDEX IF NOT EXISTS idx_lease_clause_history_effective_dates ON lease_clause_history(effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_lease_clause_history_current ON lease_clause_history(is_current) WHERE is_current = TRUE;


-- ============================================================================
-- AMENDMENT_RELATIONSHIPS TABLE
-- Tracks relationships between amendments (supersedes, supplements, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS amendment_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    amendment_id UUID NOT NULL REFERENCES amendments(id) ON DELETE CASCADE,
    related_amendment_id UUID NOT NULL REFERENCES amendments(id) ON DELETE CASCADE,
    
    relationship_type TEXT NOT NULL,  -- SUPERSEDES, SUPPLEMENTS, CLARIFIES, REVERSES
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent self-references
    CHECK (amendment_id != related_amendment_id)
);

CREATE INDEX IF NOT EXISTS idx_amendment_relationships_amendment ON amendment_relationships(amendment_id);


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get controlling clause value at any date
CREATE OR REPLACE FUNCTION get_controlling_clause(
    p_lease_id UUID,
    p_clause_type TEXT,
    p_as_of_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    clause_value TEXT,
    source_type TEXT,
    source_id UUID,
    version_number INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.clause_value,
        h.source_document_type,
        h.source_document_id,
        h.version_number
    FROM lease_clause_history h
    WHERE h.lease_id = p_lease_id
      AND h.clause_type = p_clause_type
      AND h.effective_from <= p_as_of_date
      AND (h.effective_to IS NULL OR h.effective_to >= p_as_of_date)
    ORDER BY h.version_number DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- Function to get amendment chain for a lease
CREATE OR REPLACE FUNCTION get_amendment_chain(p_lease_id UUID)
RETURNS TABLE (
    amendment_id UUID,
    amendment_number INTEGER,
    amendment_date DATE,
    status TEXT,
    modified_clauses TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.amendment_number,
        a.amendment_date,
        a.status,
        ARRAY_AGG(DISTINCT ac.clause_type) as modified_clauses
    FROM amendments a
    LEFT JOIN amendment_clauses ac ON a.id = ac.amendment_id
    WHERE a.lease_id = p_lease_id
    GROUP BY a.id, a.amendment_number, a.amendment_date, a.status
    ORDER BY a.amendment_number ASC;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- ROW LEVEL SECURITY (Optional - enable if using Supabase RLS)
-- ============================================================================
-- ALTER TABLE amendments ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE amendment_clauses ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE lease_clause_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE amendment_relationships ENABLE ROW LEVEL SECURITY;


-- ============================================================================
-- SAMPLE QUERIES FOR AMENDMENT RESOLUTION GRAPH™
-- ============================================================================

-- Query 1: Get all amendments for a lease with their modified clauses
-- SELECT * FROM get_amendment_chain('lease-uuid-here');

-- Query 2: Get controlling value for a specific clause at a specific date
-- SELECT * FROM get_controlling_clause('lease-uuid-here', 'Base Rent', '2025-01-01');

-- Query 3: Get full amendment history for a clause
-- SELECT * FROM lease_clause_history
-- WHERE lease_id = 'lease-uuid-here' AND clause_type = 'Base Rent'
-- ORDER BY version_number ASC;

-- Query 4: Find all leases with amendments modifying rent
-- SELECT DISTINCT l.id, l.property_address, COUNT(a.id) as amendment_count
-- FROM leases l
-- JOIN amendments a ON l.id = a.lease_id
-- JOIN amendment_clauses ac ON a.id = ac.amendment_id
-- WHERE ac.clause_type ILIKE '%rent%'
-- GROUP BY l.id, l.property_address;
