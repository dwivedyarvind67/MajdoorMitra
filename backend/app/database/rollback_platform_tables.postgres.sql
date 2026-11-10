-- Safe rollback for the additive MazdoorMitra 2.0 platform tables and evidence metadata.
-- Refuses to discard any data created in the new tables or new evidence fields.
DO $$
BEGIN
    IF to_regclass('public.savings_goals') IS NOT NULL AND EXISTS (SELECT 1 FROM public.savings_goals) THEN
        RAISE EXCEPTION 'savings_goals contains rows; export before rollback';
    END IF;
    IF to_regclass('public.reminders') IS NOT NULL AND EXISTS (SELECT 1 FROM public.reminders) THEN
        RAISE EXCEPTION 'reminders contains rows; export before rollback';
    END IF;
    IF to_regclass('public.reminder_preferences') IS NOT NULL AND EXISTS (SELECT 1 FROM public.reminder_preferences) THEN
        RAISE EXCEPTION 'reminder_preferences contains rows; export before rollback';
    END IF;
    IF to_regclass('public.voice_generation_history') IS NOT NULL AND EXISTS (SELECT 1 FROM public.voice_generation_history) THEN
        RAISE EXCEPTION 'voice_generation_history contains rows; export before rollback';
    END IF;
    IF to_regclass('public.worker_preferences') IS NOT NULL AND EXISTS (SELECT 1 FROM public.worker_preferences) THEN
        RAISE EXCEPTION 'worker_preferences contains rows; export before rollback';
    END IF;
    IF to_regclass('public.wage_calculations') IS NOT NULL AND EXISTS (SELECT 1 FROM public.wage_calculations) THEN
        RAISE EXCEPTION 'wage_calculations contains rows; export before rollback';
    END IF;
    IF to_regclass('public.wage_agreements') IS NOT NULL AND EXISTS (SELECT 1 FROM public.wage_agreements) THEN
        RAISE EXCEPTION 'wage_agreements contains rows; export before rollback';
    END IF;
    IF to_regclass('public.worksites') IS NOT NULL AND EXISTS (SELECT 1 FROM public.worksites) THEN
        RAISE EXCEPTION 'worksites contains rows; export before rollback';
    END IF;
    IF to_regclass('public.evidence_files') IS NOT NULL AND EXISTS (
        SELECT 1 FROM public.evidence_files
        WHERE content_type IS NOT NULL OR size_bytes IS NOT NULL OR checksum_sha256 IS NOT NULL
           OR consent_given OR work_entry_id IS NOT NULL OR payment_id IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'evidence_files has new metadata; export before rollback';
    END IF;
END $$;

DROP TABLE IF EXISTS savings_goals;
DROP TABLE IF EXISTS reminders;
DROP TABLE IF EXISTS reminder_preferences;
DROP TABLE IF EXISTS voice_generation_history;
DROP TABLE IF EXISTS worker_preferences;
DROP TABLE IF EXISTS wage_calculations;
DROP TABLE IF EXISTS wage_agreements;
DROP TABLE IF EXISTS worksites;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS payment_id;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS work_entry_id;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS consent_given;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS checksum_sha256;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS size_bytes;
ALTER TABLE evidence_files DROP COLUMN IF EXISTS content_type;
