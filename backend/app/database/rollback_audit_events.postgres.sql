-- Safe rollback for the additive audit_events migration.
-- This intentionally refuses to drop audit history once any event has been written.
DO $$
BEGIN
    IF to_regclass('public.audit_events') IS NULL THEN
        RETURN;
    END IF;
    IF EXISTS (SELECT 1 FROM public.audit_events) THEN
        RAISE EXCEPTION 'audit_events is not empty; export and retain the audit history before rollback';
    END IF;
    DROP TABLE public.audit_events;
END $$;
