-- Create table to store complete JSON plans
-- Run this SQL in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.teacher_plans (
    plan_id text NOT NULL PRIMARY KEY,
    subject_id text,
    subject text,
    grade text,
    complete_json text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT teacher_plans_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id)
);

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_teacher_plans_subject_id ON public.teacher_plans(subject_id);
CREATE INDEX IF NOT EXISTS idx_teacher_plans_created_at ON public.teacher_plans(created_at);

