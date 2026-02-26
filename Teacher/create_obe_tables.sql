-- ==============================================================================
-- OBE (Outcome Based Education) Schema - Simplified Strategy
-- Phase 1: Database Implementation
-- Strategy: Assessment-Level Alignment (No question-level tagging needed)
-- ==============================================================================

-- 1. Program Outcomes (POs)
-- Standard NBA Outcomes (PO1-PO12). Static and Global.
CREATE TABLE IF NOT EXISTS public.program_outcomes (
    po_id text NOT NULL PRIMARY KEY,         -- 'PO1', 'PO2'...
    title text NOT NULL,                     -- 'Engineering Knowledge'
    description text NOT NULL,               -- Full text
    created_at timestamp with time zone DEFAULT now()
);

-- Seed Standard NBA POs (We can run this safely as UPSERT equivalent logic or just Insert if empty)
INSERT INTO public.program_outcomes (po_id, title, description) VALUES
('PO1', 'Engineering knowledge', 'Apply mathematics, science, and computing fundamentals'),
('PO2', 'Problem analysis', 'Identify, formulate, and analyze complex computing problems'),
('PO3', 'Design/development of solutions', 'Design systems meeting specified needs'),
('PO4', 'Conduct investigations', 'Research-based analysis, experimentation, interpretation'),
('PO5', 'Modern tool usage', 'Use modern computing tools with awareness of limitations'),
('PO6', 'Engineer & society', 'Understand societal, legal, and ethical responsibilities'),
('PO7', 'Environment & sustainability', 'Understand environmental impact'),
('PO8', 'Ethics', 'Professional ethics and responsibilities'),
('PO9', 'Individual & teamwork', 'Function effectively in teams'),
('PO10', 'Communication', 'Effective oral & written communication'),
('PO11', 'Project management & finance', 'Apply management principles'),
('PO12', 'Life-long learning', 'Engage in independent and lifelong learning')
ON CONFLICT (po_id) DO UPDATE SET 
    title = EXCLUDED.title, 
    description = EXCLUDED.description;


-- 2. Course Outcomes (COs)
-- Defined by TEACHERS per SUBJECT.
-- Modular Design: Subject -> Many COs
CREATE TABLE IF NOT EXISTS public.course_outcomes (
    co_id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    subject_id text NOT NULL,                -- e.g., 'btech_cs_ds_y2'
    co_code text NOT NULL,                   -- 'CO1', 'CO2'... (Displayed to user)
    description text NOT NULL,               -- 'Understand the concepts...'
    target_threshold integer DEFAULT 60,     -- Success threshold (e.g. 60%)
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    
    -- Constraint: Unique CO code per subject
    CONSTRAINT uniq_co_per_subject UNIQUE (subject_id, co_code)
);

-- Index for fast lookup by subject
CREATE INDEX IF NOT EXISTS idx_course_outcomes_subject ON public.course_outcomes(subject_id);


-- 3. CO-PO Mapping (The Matrix)
-- Links a CO to a PO with a weight (1=Low, 2=Medium, 3=High)
CREATE TABLE IF NOT EXISTS public.co_po_mapping (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    co_id uuid NOT NULLREFERENCES public.course_outcomes(co_id) ON DELETE CASCADE,
    po_id text NOT NULL REFERENCES public.program_outcomes(po_id) ON DELETE CASCADE,
    weight integer NOT NULL CHECK (weight >= 1 AND weight <= 3), -- NBA Standard Scale
    
    -- Constraint: Prevent duplicate mappings
    CONSTRAINT uniq_co_po_map UNIQUE (co_id, po_id)
);


-- 4. Module-to-CO Mapping (The Simplified Strategy)
-- Maps an Assessment (Module) to a CO.
-- "This Module contributes to this CO"
CREATE TABLE IF NOT EXISTS public.module_co_mapping (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    module_id text NOT NULL,                 -- Matches 'module_id' in modules table
    co_id uuid NOT NULL REFERENCES public.course_outcomes(co_id) ON DELETE CASCADE,
    contribution numeric DEFAULT 1.0,        -- 1.0 = Full Module, 0.5 = Partial
    
    created_at timestamp with time zone DEFAULT now()
);

-- Index for Analytics
CREATE INDEX IF NOT EXISTS idx_mod_co_map_module ON public.module_co_mapping(module_id);
CREATE INDEX IF NOT EXISTS idx_mod_co_map_co ON public.module_co_mapping(co_id);

-- RLS Policies (Optional but recommended - Basic Open Access for Prototype)
-- ALTER TABLE public.course_outcomes ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Enable read/write for auth users" ON public.course_outcomes FOR ALL USING (auth.role() = 'authenticated');
