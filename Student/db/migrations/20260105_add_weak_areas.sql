-- Migration: Add weak_areas column to student_analytics
-- Date: 2026-01-05
-- Description: Adds a JSONB column to store frequency map of weak areas.

ALTER TABLE student_analytics 
ADD COLUMN IF NOT EXISTS weak_areas JSONB DEFAULT '{}'::jsonb;

-- Optional: Comment on column
COMMENT ON COLUMN student_analytics.weak_areas IS 'Frequency map of topics where student answered incorrectly. Format: {topic_id: {name: string, count: int}}';
